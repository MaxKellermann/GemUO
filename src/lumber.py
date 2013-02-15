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

from twisted.python import log
from twisted.internet import reactor
from uo.skills import *
from uo.entity import *
import gemuo.config
from gemuo.simple import simple_run, simple_later
from gemuo.data import TileCache
from gemuo.map import BridgeMap, WorldMap, CacheMap
from gemuo.entity import Position
from gemuo.locations import nearest_bank, is_rel_por
from gemuo.exhaust import ExhaustDatabase
from gemuo.resource import find_statics_resource_block, reachable_resource
from gemuo.defer import deferred_find_player_item
from gemuo.target import Target
from gemuo.engine import Engine
from gemuo.engine.messages import PrintMessages
from gemuo.engine.guards import Guards
from gemuo.engine.equip import Equip
from gemuo.engine.lumber import Lumber
from gemuo.engine.walk import PathFindWalkRectangle, PathFindWalkAny
from gemuo.engine.watch import Watch
from gemuo.engine.items import OpenBank
from gemuo.engine.restock import Restock
from gemuo.engine.death import AutoResurrect
from gemuo.engine.gm import DetectGameMaster
from gemuo.engine.relpor import RelPorCaptcha
from gemuo.engine.training import SkillTraining
from gemuo.engine.boards_relpor import MakeBoardsRelpor


BANK = None

def find_tree(map, exhaust_db, position):
    center = Position((position.x * 7 + BANK[4]) / 8,
                      (position.y * 7 + BANK[5]) / 8)
    return find_statics_resource_block(map, center, TREES, exhaust_db)

def passable_positions_around(map, x, y, z, distance):
    positions = []
    for ix in range(x - distance, x + distance + 1):
        for iy in range(y - distance, y + distance + 1):
            if map.is_passable(ix, iy, z):
                positions.append((ix, iy))
    return positions

class AutoLumber(Engine):
    def __init__(self, client, map, exhaust_db):
        Engine.__init__(self, client)
        self.world = client.world
        self.player = client.world.player
        self.map = map
        self.exhaust_db = exhaust_db

        if self.player.mass_remaining() < 50:
            self._success()
            return

        self._walk()

    def _lumbered(self, result):
        if self.player.is_dead() or self.player.mass_remaining() < 50 or self.world.combatant is not None:
            # too heavy, finish this engine
            self._success()
            return

        reactor.callLater(0.5, self._make_boards)

    def _make_boards(self):
        if is_rel_por(self.world):
            MakeBoardsRelpor(self._client)

        reactor.callLater(0.5, self._walk)

    def _equipped(self, result):
        tree = reachable_resource(self.player.position, self.trees, 2)
        if tree is None:
            print "No tree??"
            reactor.callLater(0.5, self._walk)
            return

        tree = Target(x=tree.x, y=tree.y, z=tree.z, graphic=tree.item_id)
        d = Lumber(self._client, self.map, tree, self.exhaust_db).deferred
        d.addCallbacks(self._lumbered, self._success)

    def _walked(self, result):
        # make sure an axe is equipped
        d = Equip(self._client, lambda x: x.item_id in ITEMS_AXE).deferred
        d.addCallbacks(self._equipped, self._failure)

    def _walk_failed(self, fail):
        # walking to this tree failed for some reason; mark this 8x8
        # as "exhausted", so we won't try it again for a while
        tree = self.trees[0]
        self.exhaust_db.set_exhausted(tree.x/8, tree.y/8)
        self._walk()

    def _walk(self):
        position = self.player.position
        if position is None:
            self._failure()
            return

        self.trees = find_tree(self.map, self.exhaust_db, position)
        if self.trees is None:
            self._failure()
            return

        positions = set()
        for resource in self.trees:
            for p in passable_positions_around(self.map, resource.x, resource.y, resource.z, 2):
                positions.add(Position(p[0], p[1]))

        self.map.flush_cache()
        d = PathFindWalkAny(self._client, self.map, positions).deferred
        d.addCallbacks(self._walked, self._walk_failed)

class Bank(Engine):
    def __init__(self, client, map):
        Engine.__init__(self, client)
        self._map = map
        self.tries = 5

        print "Bank"
        self._walk()

    def _walk(self):
        self._map.flush_cache()
        d = PathFindWalkRectangle(self._client, self._map, BANK).deferred
        d.addCallbacks(self._walked, self._walk_failed)

    def _walk_failed(self, fail):
        if self._client.is_dead():
            self._success()
            return

        self.tries -= 1
        if self.tries > 0:
            self._walk()
        else:
            self._failure(fail)

    def _walked(self, result):
        d = OpenBank(self._client).deferred
        d.addCallbacks(self._opened, self._walk_failed)

    def _out_filter(self, x):
        return x.item_id not in ITEMS_AXE

    def _opened(self, bank):
        d = Restock(self._client, bank, func=self._out_filter,
                    counts=((ITEMS_AXE, 1),)).deferred
        d.addCallbacks(self._restocked, self._failure)

    def _restocked(self, result):
        self._success()

class AutoHarvest(Engine):
    def __init__(self, client, map, exhaust_db):
        Engine.__init__(self, client)
        self.world = client.world
        self.player = client.world.player
        self.map = map
        self.exhaust_db = exhaust_db

        self._check()

    def _restocked(self, result):
        if self.player.is_dead():
            log.msg("Waiting for resurrection")
            reactor.callLater(10, self._check)
            return

        if self.world.combatant is not None:
            log.msg("Waiting until combat is over")
            reactor.callLater(5, self._restocked, result)
            return

        self._begin_lumber()

    def _restock(self):
        d = Bank(self._client, self.map).deferred
        d.addCallbacks(self._restocked, self._failure)

    def _found_axe(self, axe):
        self._begin_lumber()

    def _no_axe(self, fail):
        self._restock()

    def _check(self):
        if self.player.is_dead():
            log.msg("Waiting for resurrection")
            reactor.callLater(10, self._check)
        elif self.player.mass_remaining() < 50 or self.world.combatant is not None:
            log.msg("Flee to safe place until combat is over")
            self._restock()
        else:
            d = deferred_find_player_item(self._client, lambda x: x.item_id in ITEMS_AXE)
            d.addCallbacks(self._found_axe, self._no_axe)

    def _lumbered(self, result):
        self._check()

    def _begin_lumber(self):
        d = AutoLumber(self._client, self.map, self.exhaust_db).deferred
        d.addCallbacks(self._lumbered, self._failure)

def begin(client):
    tc = TileCache(gemuo.config.require_data_path())
    m = CacheMap(WorldMap(BridgeMap(tc.get_map(0)), client.world))
    exhaust_db = ExhaustDatabase('/tmp/trees.db')

    global BANK
    BANK = nearest_bank(client.world, client.world.player.position)

    AutoResurrect(client, m)

    #return Bank(client, m)
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
