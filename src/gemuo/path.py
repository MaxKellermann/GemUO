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

# Implementation of the A* path finding algorithm.

import heapq
from uo.entity import *

class Unreachable(Exception):
    """The position is not reachable."""
    pass

class Position:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self):
        return '(%d,%d)' % (self.x, self.y)

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return self.x << 16 | self.y

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __add__(self, other):
        return Position(self.x + other.x, self.y + other.y)

    def manhattan_distance(self, other):
        return abs(self.x - other.x) + abs(self.y - other.y)

    def square_distance(self, other):
        return (self.x - other.x) * (self.x - other.x) \
               + (self.y - other.y) * (self.y - other.y)

direction_vectors = (
    Position(0, -1),
    Position(1, -1),
    Position(1, 0),
    Position(1, 1),
    Position(0, 1),
    Position(-1, 1),
    Position(-1, 0),
    Position(-1, -1),
)

def passable_to(map, source, direction):
    vector = direction_vectors[direction]
    destination = source + vector
    if not map.is_passable(destination.x, destination.y, 0):
        return False
    if vector.x == 0 or vector.y == 0:
        return True

    # for diagonal moves, we need those to be passable, too
    return map.is_passable(source.x, source.y + vector.y, 0) and \
           map.is_passable(source.x + vector.x, source.y, 0)

def step(map, position):
    """Generator which emits all passable positions surrounding the
    specifid position."""
    for i in range(len(direction_vectors)):
        if passable_to(map, position, i):
            yield position + direction_vectors[i], i

def walk_back(l, dest):
    """Generates the whole path, i.e. a list of positions."""
    path = [dest]
    while True:
        total, cost, src, direction = l[dest]
        if direction is None:
            break
        dest = dest + direction_vectors[(direction + 4) % 8]
        path.append(dest)
    return list(reversed(path))[1:]

def path_find(map, src, dest):
    if not map.is_passable(dest.x, dest.y, 0):
        # the destination cannot possibly be reached
        raise Unreachable()

    src = Position(src.x, src.y)
    dest = Position(dest.x, dest.y)
    if src == dest:
        # no-op
        return ()

    # ( total_cost, cost, src, direction )
    queue = [ (0, 0, src, None) ]
    open_list = { src: queue[0] }
    closed_list = dict()

    limit = max(dest.square_distance(src), 4000) * 4
    for j in range(limit):
        if len(queue) == 0:
            raise Unreachable()

        # find the nearest position on the "open" list, and move it to
        # the "closed" list
        nearest = heapq.heappop(queue)
        total, cost, p, direction = nearest
        del open_list[p]
        closed_list[p] = nearest

        # calculate the cost of all surrounding tiles
        cost += 1
        for n, d in step(map, p):
            if n in closed_list or n in open_list:
                continue

            n_cost = cost
            if d != direction:
                # direction change is one more walk packet
                n_cost += 1

            distance = dest.manhattan_distance(n)
            item = (n_cost + distance, n_cost, n, d)
            heapq.heappush(queue, item)
            open_list[n] = item
            if distance == 0:
                # destination has been reached - terminate
                closed_list[n] = item
                return walk_back(closed_list, dest)

    # give up
    raise Unreachable()
