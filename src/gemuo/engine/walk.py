#
#  GemUO
#
#  (c) 2005-2010 Max Kellermann <max@duempel.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; version 2 of the License.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#

from random import Random
from twisted.internet import reactor, threads
from uo.entity import *
from gemuo.error import *
from gemuo.entity import Position
from gemuo.engine import Engine
from gemuo.path import path_find, Unreachable

random = Random()

class WalkReject(Exception):
    def __init__(self, message='Walk reject'):
        Exception.__init__(self, message)

class Blocked(Exception):
    """The calculated path or the destination is blocked (temporary
    failure)."""
    def __init__(self, position):
        Exception.__init__(self)
        self.position = position

def should_run(mobile):
    return mobile.stamina is not None and \
           (mobile.stamina.value >= 20 or \
            mobile.stamina.value >= mobile.stamina.limit / 2)

class WalkPoint:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self):
        return "(%d,%d)" % (self.x, self.y)

class DirectWalk(Engine):
    def __init__(self, client, destination):
        Engine.__init__(self, client)

        self.player = client.world.player
        self.walk = client.world.walk
        self.destination = destination

        self._next_walk()

    def _direction_from(self, position):
        destination = self.destination
        if destination.x < position.x:
            if destination.y < position.y:
                return NORTH_WEST
            elif destination.y > position.y:
                return SOUTH_WEST
            else:
                return WEST
        elif destination.x > position.x:
            if destination.y < position.y:
                return NORTH_EAST
            elif destination.y > position.y:
                return SOUTH_EAST
            else:
                return EAST
        else:
            if destination.y < position.y:
                return NORTH
            elif destination.y > position.y:
                return SOUTH
            else:
                return None

    def _next_walk(self):
        player = self.player
        position = player.position
        if position is None:
            self._failure(MissingData('Player position is missing'))
            return

        direction = self._direction_from(position)
        if direction is None:
            if self.walk.finished():
                self._success()
            return

        if should_run(player):
            direction |= RUNNING

        packet = self.walk.walk(direction)
        if packet is None:
            return
        self._client.send(packet)
        self._next_walk()

    def on_walk_reject(self):
        self._failure(WalkReject())

    def on_walk_ack(self):
        self._next_walk()

class PathWalk(Engine):
    def __init__(self, client, path):
        Engine.__init__(self, client)

        self.player = client.world.player
        self.path = list(path)
        self.__walk = None

        self._next_walk()

    def abort(self):
        if self.__walk is not None:
            self.__walk.cancel()
            self.__walk = None
        Engine.abort(self)

    def _distance2(self, position):
        player = self.player.position
        dx = player.x - position.x
        dy = player.y - position.y
        return dx*dx + dy*dy

    def _next_walk(self):
        # find nearest point
        nearest = None
        nearest_distance2 = 999999

        for x in self.path:
            distance2 = self._distance2(x)
            if distance2 < nearest_distance2:
                nearest = x
                nearest_distance2 = distance2

        if nearest is None:
            print "done"
            self._success()

        while self.path[0] != nearest:
            self.path = self.path[1:]

        if nearest_distance2 == 0:
            self.path = self.path[1:]
            self._next_walk()
            return

        print "Walk to", nearest, nearest_distance2
        self.__walk = DirectWalk(self._client, nearest).deferred
        self.__walk.addCallbacks(self._walked, self._walk_failed)

    def _walked(self, result):
        self.__walk = None
        self.path = self.path[1:]
        self._next_walk()

    def _walk_failed(self, fail):
        print "Walk failed", fail
        self.__walk = None
        reactor.callLater(2, self._next_walk)

class PathFindWalkFragile(Engine):
    def __init__(self, client, map, destination):
        Engine.__init__(self, client)

        self.player = client.world.player
        self.walk = client.world.walk
        self.map = map
        self.destination = destination
        self._sent = []

        if self.player.position.x == destination.x and \
           self.player.position.y == destination.y:
            self._success()
            return

        map.flush_cache()
        self.__find = threads.deferToThread(path_find, map, self.player.position, destination)
        self.__find.addCallbacks(self._path_found, self._failure)

    def abort(self):
        if self.__find is not None:
            self.__find.cancel()
            self.__find = None
        Engine.abort(self)

    def _direction(self, src, dest):
        if dest.x < src.x:
            if dest.y < src.y:
                return NORTH_WEST
            elif dest.y > src.y:
                return SOUTH_WEST
            else:
                return WEST
        elif dest.x > src.x:
            if dest.y < src.y:
                return NORTH_EAST
            elif dest.y > src.y:
                return SOUTH_EAST
            else:
                return EAST
        else:
            if dest.y < src.y:
                return NORTH
            elif dest.y > src.y:
                return SOUTH
            else:
                return None

    def _next_walk(self):
        if len(self._path) == 0:
            if self.player.position.x == self.destination.x and \
                   self.player.position.y == self.destination.y:
                self._success()
            else:
                self._failure(Blocked(None))
            return

        next = self._path[0]

        player = self.player
        position = player.position

        if position is None:
            self._failure(MissingData('Player position is missing'))
            return

        m = self.map
        m.flush_cache()

        for q in self._path:
            if not self.map.is_passable(q.x, q.y, position.z):
                self._failure(Blocked(q))
                return

        direction = self._direction(position, next)
        if direction is None:
            self._path = self._path[1:]
            self._next_walk()
            return

        if should_run(player):
            direction |= RUNNING

        w = self.walk.walk(direction)
        if w is None:
            self._failure()
            return

        self._client.send(w)
        self._sent.append(next)

    def _path_found(self, path):
        assert path is not None

        self.__find = None
        self._path = list(path)
        self._sent = [self.player.position]
        self._next_walk()

    def _cleanup(self):
        position = self.player.position
        while len(self._sent) > 0:
            i = self._sent[0]
            if i.x == position.x and i.y == position.y:
                return True
            self._sent = self._sent[1:]
        return False

    def on_walk_reject(self):
        if self.__find is not None:
            # not our reject, we're still finding the path
            return

        if self._cleanup() and len(self._sent) >= 2:
            to = self._sent[1]
        else:
            to = None
        print "walk reject", to

        self._failure(Blocked(to))

    def on_walk_ack(self):
        if self.__find is not None:
            # not our reject, we're still finding the path
            return

        self._cleanup()
        self._next_walk()

class MapWrapper:
    def __init__(self, map):
        self.map = map
        self.bad = []

    def reset(self):
        self.bad = []

    def is_passable(self, x, y, z):
        from gemuo.path import Position
        return self.map.is_passable(x, y, z) and Position(x, y) not in self.bad

    def add_bad(self, x, y):
        from gemuo.path import Position
        self.bad.append(Position(x, y))

    def __getattr__(self, name):
        x = getattr(self.map, name)
        setattr(self, name, x)
        return x

class PathFindWalk(Engine):
    def __init__(self, client, map, destination):
        Engine.__init__(self, client)

        self.player = client.world.player
        self.map = MapWrapper(map)
        self.destination = destination

        self._try()

    def _try(self):
        d = PathFindWalkFragile(self._client, self.map, self.destination).deferred
        d.addCallbacks(self._success, self._walk_failed)

    def _walk_failed(self, failure):
        if not self.map.is_passable(self.destination.x, self.destination.y,
                                    self.player.position.z):
            self._failure(failure)
            return

        if failure.check(Blocked):
            p = failure.value.position
            if p is not None:
                if self.map.is_passable(p.x, p.y, self.player.position.z):
                    self.map.add_bad(p.x, p.y)
                else:
                    self.map.reset()

        self._try()

def choose_destination(map, player_position, destinations):
    destinations = filter(lambda p: map.is_passable(p.x, p.y, 0),
                          destinations)
    if len(destinations) == 0:
        return None

    destinations = list(destinations)

    def cmp_distance(a, b):
        return cmp(player_position.manhattan_distance(a),
                   player_position.manhattan_distance(b))

    destinations.sort(cmp=cmp_distance)
    if len(destinations) > 8:
        destinations = destinations[0:len(destinations)/2]
    return destinations[random.randint(0, len(destinations) - 1)]

class PathFindWalkAny(Engine):
    def __init__(self, client, map, destinations):
        Engine.__init__(self, client)

        self.player = client.world.player
        self.map = MapWrapper(map)
        self.destinations = destinations

        self._try()

    def _try(self):
        destination = choose_destination(self.map,
                                         self.player.position,
                                         self.destinations)
        if destination is None:
            self._failure(Unreachable())
            return

        d = PathFindWalkFragile(self._client, self.map, destination).deferred
        d.addCallbacks(self._success, self._walk_failed)

    def _walk_failed(self, failure):
        if failure.check(Blocked):
            p = failure.value.position
            if p is not None:
                if self.map.is_passable(p.x, p.y, self.player.position.z):
                    self.map.add_bad(p.x, p.y)
                else:
                    self.map.reset()

        self._try()

def PathFindWalkRectangle(client, map, rectangle):
    assert rectangle[0] <= rectangle[2]
    assert rectangle[1] <= rectangle[3]

    destinations = []
    for x in range(rectangle[0], rectangle[2] + 1):
        destinations.append(Position(x, rectangle[1]))
        destinations.append(Position(x, rectangle[3]))

    for y in range(rectangle[1] + 1, rectangle[3]):
        destinations.append(Position(rectangle[0], y))
        destinations.append(Position(rectangle[2], y))

    return PathFindWalkAny(client, map, destinations)

class PathFindWalkNear(Engine):
    def __init__(self, client, map, destination, distance):
        Engine.__init__(self, client)

        self.player = client.world.player
        self.map = MapWrapper(map)
        self.destination = destination
        self.distance = distance
        self.__walk = None

        self._try()

    def abort(self):
        if self.__walk is not None:
            self.__walk.cancel()
            self.__walk = None
        Engine.abort(self)

    def _try(self):
        destinations = []

        for x in range(self.destination.x - self.distance,
                       self.destination.x + self.distance):
            for y in range(self.destination.y - self.distance,
                           self.destination.y + self.distance):
                p = Position(x, y)
                if self.destination.manhattan_distance(p) < self.distance:
                    destinations.append(p)

        destination = choose_destination(self.map,
                                         self.player.position,
                                         destinations)
        if destination is None:
            self._failure(Unreachable())
            return

        self.__walk = d = PathFindWalkFragile(self._client, self.map, destination).deferred
        self.__walk.addCallbacks(self._success, self._walk_failed)

    def _walk_failed(self, failure):
        self.__walk = None

        if failure.check(Blocked):
            p = failure.value.position
            if p is not None:
                if self.map.is_passable(p.x, p.y, self.player.position.z):
                    self.map.add_bad(p.x, p.y)
                else:
                    self.map.reset()
        elif failure.check(Unreachable):
            self._failure(failure)
            return

        self._try()
