#!/usr/bin/python
#
#  GemUO
#
#  (c) 2005-2012 Max Kellermann <max@duempel.org>
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

import logging
from twisted.python import log
from twisted.internet import reactor
import uo.packets as p
from uo.skills import *
from uo.entity import *
import gemuo.config
from gemuo.entity import Item
from gemuo.locations import nearest_bank, nearest_forge
from gemuo.simple import simple_run, simple_later
from gemuo.data import TileCache
from gemuo.map import BridgeMap, WorldMap, CacheMap
from gemuo.entity import Position
from gemuo.exhaust import ExhaustDatabase
from gemuo.resource import find_land_resource
from gemuo.statics import find_static_near
from gemuo.target import Target
from gemuo.defer import deferred_find_player_item, deferred_find_item_in_backpack, deferred_amount_in_backpack
from gemuo.error import *
from gemuo.engine import Engine
from gemuo.engine.messages import PrintMessages
from gemuo.engine.guards import Guards
from gemuo.engine.mine import Mine, MergeOre
from gemuo.engine.walk import PathFindWalk, PathFindWalkRectangle, PathFindWalkNear, DirectWalk
from gemuo.engine.watch import Watch
from gemuo.engine.items import OpenContainer, OpenBank
from gemuo.engine.restock import Restock
from gemuo.engine.death import AutoResurrect
from gemuo.engine.gm import DetectGameMaster
from gemuo.engine.relpor import RelPorCaptcha
from gemuo.engine.items import UseAndTarget
from gemuo.engine.training import SkillTraining

def passable_positions_around(map, x, y, z, distance):
    positions = []
    for ix in range(x - distance, x + distance + 1):
        for iy in range(y - distance, y + distance + 1):
            if map.is_passable(ix, iy, z):
                positions.append((ix, iy))
    return positions

def find_mountain(map, exhaust_db, position):
    def check_mountain(item_id, x, y, z):
        return len(passable_positions_around(map, x, y, z, 2)) > 0

    #center = Position((position.x * 3 + CENTER[0]) / 4,
    #                  (position.y * 3 + CENTER[1]) / 4)
    center = position
    return find_land_resource(map, position, MOUNTAIN, exhaust_db, check_mountain)

class AutoMine(Engine):
    def __init__(self, client, map, exhaust_db):
        Engine.__init__(self, client)
        self.world = client.world
        self.player = client.world.player
        self.map = map
        self.exhaust_db = exhaust_db

        if self.player.mass_remaining() < 30:
            self._success()
            return

        self._walk()

    def _walk_failed(self, fail):
        # walking to this tree failed for some reason; mark this 8x8
        # as "exhausted", so we won't try it again for a while
        self.exhaust_db.set_exhausted(self.mountain.x/8, self.mountain.y/8)
        self._walk()

    def _walk(self):
        position = self.player.position
        if position is None:
            self._failure()
            return

        self.mountain = find_mountain(self.map, self.exhaust_db, position)
        if self.mountain is None:
            self._failure()
            return

        log.msg("mountain %s" % self.mountain)
        self.map.flush_cache()
        d = PathFindWalkNear(self._client, self.map, self.mountain, 2).deferred
        d.addCallbacks(self._walked, self._walk_failed)

    def _walked(self, result):
        d = Mine(self._client, self.map, self.mountain, self.exhaust_db).deferred
        d.addCallbacks(self._mined, self._failure)

    def _mined(self, result):
        if self.player.is_dead() or self.player.mass_remaining() < 30 or self.world.combatant is not None:
            # too heavy, finish this engine
            self._success()
            return

        self._walk()

def player_can_melt(player):
    return player.is_skill_above(player, SKILL_MINING, 35)

def is_ore(i):
    return i.item_id in ITEMS_ORE

def can_melt(i):
    if i.item_id == ITEM_ORE_TINY:
        return i.amount >= 2

    return i.item_id in ITEMS_ORE

def group_by_hue(items):
    result = dict()
    for i in items:
        if i.hue not in result:
            result[i.hue] = [i]
        else:
            result[i.hue].append(i)
    return result

def find_two_same_hue(items):
    for i in group_by_hue(items).itervalues():
        if len(i) >= 2:
            return i
    return None

def find_reachable_target(map, world, ids):
    item = world.find_reachable_item(lambda x: x.item_id in ids)
    if item is not None:
        return item

    position = world.player.position
    static = find_static_near(map, position.x, position.y, 2, ids)
    if static is not None:
        return Target(x=static.x, y=static.y, z=static.z, graphic=static.item_id)

    return None

def reachable_forge_target(map, world):
    return find_reachable_target(map, world, ITEMS_FORGE)

class Melt(Engine):
    def __init__(self, client, map):
        Engine.__init__(self, client)
        self._map = map
        self.__tries = 5

        d = deferred_find_item_in_backpack(self._client, can_melt)
        d.addCallbacks(self._found_ore, self._no_ore)

    def _no_ore(self, fail):
        self._success()

    def _found_ore(self, ore):
        self.ore = ore

        if reachable_forge_target(self._map, self._client.world) is None:
            self._walk()
        else:
            self._walked()

    def _walk(self):
        forge = nearest_forge(self._client.world, self._client.world.player.position)
        print "forge", forge
        self._map.flush_cache()
        p = Position(forge[0], forge[1])
        d = PathFindWalkNear(self._client, self._map, p, 1).deferred
        d.addCallbacks(self._walked, self._walk_failed)

    def _walk_failed(self, fail):
        self.__tries -= 1
        if self.__tries > 0:
            self._walk()
        else:
            self._failure(fail)

    def _walked(self, *args):
        print "resync"
        self._client.send(p.Resync())

        #backpack = client.world.backpack()
        #if backpack is not None:
        #    d = MergeOre(self._client, backpack).deferred
        #    d.addCallbacks(self._merged_ore, self._merged_ore)
        #else:
        self._melt(self.ore)

    def _merged_ore(self, *args):
        self._melt(self.ore)

    def _melt(self, ore):
        forge = reachable_forge_target(self._map, self._client.world)
        if forge is None:
            self._failure(NoSuchEntity('No forge'))
            return

        d = UseAndTarget(self._client, ore, forge).deferred
        d.addCallbacks(self._melted, self._failure)

    def _melted(self, result):
        reactor.callLater(1, self._more)

    def _more(self):
        d = deferred_find_item_in_backpack(self._client, can_melt)
        d.addCallbacks(self._more_ore, self._no_ore)

    def _more_ore(self, ore):
        self._melt(ore)

def find_door_at(world, x, y):
    for e in world.iter_entities_at(x, y):
        if isinstance(e, Item) and e.parent_serial is None and e.item_id in range(0x6a5, 0x6ad):
            return e
    return None

def find_box_at(world, x, y):
    for e in world.iter_entities_at(x, y):
        if isinstance(e, Item) and e.item_id in ITEMS_CONTAINER:
            return e
    return None

class OpenDoor(Engine):
    def __init__(self, client, x, y):
        Engine.__init__(self, client)

        self.__tries = 5
        self.x = x
        self.y = y
        self._next()

    def _next(self):
        door = find_door_at(self._client.world, self.x, self.y)
        if door is None:
            self._success()
            return

        self.__tries -= 1
        if self.__tries <= 0:
            self._failure()
            return

        self._client.send(p.Use(door.serial))
        reactor.callLater(0.5, self._next)

def restock_miner(client, bank):
    def out_filter(x):
        if x.item_id in ITEMS_MINING_TOOLS: return False

        if player_can_melt(client.world.player) and \
           x.item_id in ITEMS_ORE:
            return False

        return True

    counts = (
        (ITEMS_MINING_TOOLS, 3),

        # only if STR=100:
        #(ITEMS_ORE, 82),
    )

    return Restock(client, bank, func=out_filter,
                   counts=counts).deferred

class HouseRestockGlue(Engine):
    def __init__(self, client, map):
        Engine.__init__(self, client)
        self._map = map
        self.__tries = 5

        self._walk()

    def _walk(self):
        self._map.flush_cache()
        d = PathFindWalk(self._client, self._map, Position(HOUSE[0], HOUSE[1])).deferred
        d.addCallbacks(self._walked, self._walk_failed)

    def _walk_failed(self, fail):
        self.__tries -= 1
        if self.__tries > 0:
            self._walk()
        else:
            self._failure(fail)

    def _walked(self, result):
        d = OpenDoor(self._client, HOUSE[0], HOUSE[1] - 1).deferred
        d.addCallbacks(self._opened, self._failure)

    def _opened(self, result):
        d = DirectWalk(self._client, Position(HOUSE[0], HOUSE[1] - 2)).deferred
        d.addCallbacks(self._walked2, self._walk2_failed)

    def _walked2(self, result):
        box = find_box_at(self._client.world, HOUSE[0], HOUSE[1] - 4)
        if box is None:
            self._failure(NoSuchEntity('No box'))
            return

        d = restock_miner(self._client, box)
        d.addCallbacks(self._restocked, self._failure)

    def _walk2_failed(self, fail):
        log.msg("resync", logLevel=logging.DEBUG)
        self._client.send(p.Resync())
        reactor.callLater(2, self._walk)

    def _restocked(self, result):
        d = OpenDoor(self._client, HOUSE[0], HOUSE[1] - 1).deferred
        d.addCallbacks(self._opened2, self._failure)

    def _opened2(self, result):
        d = DirectWalk(self._client, Position(HOUSE[0], HOUSE[1])).deferred
        d.addCallbacks(self._success, self._failure)

class BankRestockGlue(Engine):
    def __init__(self, client, map):
        Engine.__init__(self, client)
        self._map = map
        self.__tries = 5

        print "Bank"
        self._walk()

    def _walk(self):
        self._map.flush_cache()
        d = PathFindWalkRectangle(self._client, self._map, BANK).deferred
        d.addCallbacks(self._walked, self._walk_failed)

    def _walk_failed(self, fail):
        self.__tries -= 1
        if self.__tries > 0:
            self._walk()
        else:
            self._failure(fail)

    def _walked(self, result):
        d = OpenBank(self._client).deferred
        d.addCallbacks(self._opened, self._walk_failed)

    def _opened(self, bank):
        d = restock_miner(self._client, bank)
        d.addCallbacks(self._restocked, self._failure)

    def _restocked(self, result):
        self._success()

def RestockGlue(client, map):
    if BANK is None:
        return HouseRestockGlue(client, map)
    else:
        return BankRestockGlue(client, map)

class AutoHarvest(Engine):
    def __init__(self, client, map, exhaust_db):
        Engine.__init__(self, client)
        self.world = client.world
        self.player = client.world.player
        self.map = map
        self.exhaust_db = exhaust_db

        self._check()

    def _check(self):
        if self.player.is_dead():
            log.msg("Waiting for resurrection")
            reactor.callLater(10, self._check)
        elif self.world.combatant is not None:
            log.msg("Flee to safe place until combat is over")
            self._restock()
        elif self.player.mass_remaining() < 30:
            if player_can_melt(self.player):
                self._melt()
            else:
                self._restock()
        else:
            d = deferred_find_player_item(self._client, lambda x: x.item_id in ITEMS_MINING_TOOLS)
            d.addCallbacks(self._found_tool, self._no_tool)

    def _melt(self):
        log.msg("melt")
        d = Melt(self._client, self.map).deferred
        d.addCallbacks(self._melted, self._melt_failed)

    def _melted(self, result):
        d = deferred_amount_in_backpack(self._client, lambda i: i.item_id in ITEMS_INGOT)
        d.addCallbacks(self._ingots_counted, self._failure)

    def _melt_failed(self, fail):
        print "melt failed:", fail
        self._client.send(p.Resync())
        reactor.callLater(2, self._melt)

    def _ingots_counted(self, amount):
        log.msg("%u ingots" % amount)
        if amount >= 200 or self.player.mass_remaining() < 100:
            self._restock()
        else:
            self._check()

    def _restock(self):
        log.msg("restock")
        d = RestockGlue(self._client, self.map).deferred
        d.addCallbacks(self._restocked, self._failure)

    def _restocked(self, result):
        if self.player.is_dead():
            log.msg("Waiting for resurrection")
            reactor.callLater(10, self._check)
            return

        if self.world.combatant is not None:
            log.msg("Waiting until combat is over")
            reactor.callLater(5, self._restocked, result)
            return

        self._begin_mine()

    def _found_tool(self, tool):
        self._begin_mine()

    def _no_tool(self, fail):
        self._restock()

    def _mined(self, result):
        reactor.callLater(0.2, self._check)

    def _begin_mine(self):
        d = AutoMine(self._client, self.map, self.exhaust_db).deferred
        d.addCallbacks(self._mined, self._mine_failed)

    def _mine_failed(self, fail):
        if isinstance(fail.value, NoSuchEntity):
            self._restock()
        else:
            self._failure(fail)

def begin(client):
    tc = TileCache(gemuo.config.require_data_path())
    m = CacheMap(WorldMap(BridgeMap(tc.get_map(0)), client.world))
    exhaust_db = ExhaustDatabase('/tmp/ore.db', duration=10)

    p = client.world.player.position

    global BANK
    BANK = nearest_bank(client.world, client.world.player.position)

    AutoResurrect(client, m)

    #return BankRestockGlue(client, m)
    return AutoHarvest(client, m, exhaust_db)

def run(client):
    Watch(client)
    Guards(client)
    DetectGameMaster(client)
    RelPorCaptcha(client)
    PrintMessages(client)
    SkillTraining(client, (SKILL_HIDING,), round_robin=False)

    return simple_later(1, begin, client)

simple_run(run)
