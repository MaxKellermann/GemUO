#!/usr/bin/python
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

from twisted.python import log
from twisted.internet import reactor
import uo.packets as p
from uo.entity import *
from gemuo.entity import Item
from gemuo.simple import simple_run
from gemuo.error import *
from gemuo.defer import deferred_find_item_in, deferred_find_item_in_recursive, deferred_amount_in
from gemuo.engine import Engine
from gemuo.engine.messages import PrintMessages
from gemuo.engine.restock import drop_into, MoveItems
from gemuo.engine.hide import AutoHide
from gemuo.engine.items import OpenContainer

ITEMS_LOCK = ITEMS_INGOT + ITEMS_ORE
ITEMS_SECURE = ITEMS_MINING_TOOLS + ITEMS_ORE
ITEMS_MERGE = ITEMS_INGOT

SECURE_COUNTS = (
    (ITEMS_MINING_TOOLS, 4),
)

def find_box_at(world, x, y):
    for e in world.iter_entities_at(x, y):
        if isinstance(e, Item) and e.item_id in ITEMS_CONTAINER:
            return e
    return None

class Merge(Engine):
    def __init__(self, client, container):
        Engine.__init__(self, client)
        self.container = container

        d = OpenContainer(client, container).deferred
        d.addCallbacks(self._opened, self._failure)

    def _opened(self, result):
        reactor.callLater(1, self._next)

    def _next(self):
        client = self._client
        world = client.world

        n = set()

        while True:
            a = world.find_item_in(self.container, lambda i: i.serial not in n and i.item_id in ITEMS_MERGE)
            if a is None:
                self._success()
                return

            n.add(a.serial)

            b = world.find_item_in(self.container, lambda i: i.serial != a.serial and i.item_id == a.item_id and i.hue == a.hue)
            if b is not None:
                break

        print "merge", a, b

        client.send(p.LiftRequest(a.serial))
        client.send(p.Drop(a.serial, 0, 0, 0, b.serial))
        reactor.callLater(1, self._next)

class MoveAmount(Engine):
    def __init__(self, client, source, destination, func, amount):
        Engine.__init__(self, client)

        assert amount > 0

        self.source = source
        self.destination = destination
        self.func = func
        self.amount = amount

        d = OpenContainer(client, destination).deferred
        d.addCallbacks(self._opened, self._failure)

    def _opened(self, result):
        reactor.callLater(1, self._next)

    def _next(self):
        d = deferred_find_item_in_recursive(self._client, self.source, self.func)
        d.addCallbacks(self._found, self._failure)

    def _found(self, i):
        amount = self.amount
        if amount > i.amount:
            amount = i.amount

        drop_into(self._client, i, self.destination, amount)

        self.amount -= amount
        if self.amount > 0:
            reactor.callLater(1, self._next)
        else:
            reactor.callLater(1, self._success)

class Janitor(Engine):
    def __init__(self, client):
        Engine.__init__(self, client)

        self.busy = False
        self.scheduled = False

        player = client.world.player.position
        self.secure_box = find_box_at(client.world, player.x, player.y + 1)
        if self.secure_box is None:
            self._failure(NoSuchEntity('No secure box'))

        self.locked_box = find_box_at(client.world, player.x, player.y - 1)
        if self.locked_box is None:
            self._failure(NoSuchEntity('No locked box'))

        self._schedule()

    def _schedule(self):
        if self.busy:
            self.scheduled = True
        else:
            reactor.callLater(1, self._merge)
            self.busy = True

    def _merge(self):
        d = Merge(self._client, self.locked_box).deferred
        d.addCallbacks(self._merged, self._failure)

    def _merged(self, result):
        self._move()

    def _move(self):
        assert self.busy
        #d = deferred_find_item_in(self._client, self.secure_box, lambda i: i.item_id in ITEMS_LOCK)
        d = deferred_find_item_in(self._client, self.secure_box, lambda i: i.item_id not in ITEMS_SECURE)
        d.addCallbacks(self._found_lock, self._not_found_lock)

    def _found_lock(self, item):
        assert self.busy
        log.msg("move %s" % item)
        drop_into(self._client, item, self.locked_box)
        reactor.callLater(1, self._move)

    def _not_found_lock(self, fail):
        self._counts = list(SECURE_COUNTS)
        reactor.callLater(1, self._check_counts)

    def _check_counts(self):
        if len(self._counts) == 0:
            self._finish()
            return

        self._count, self._counts = self._counts[0], self._counts[1:]
        d = deferred_amount_in(self._client, self.secure_box, lambda i: i.item_id in self._count[0])
        d.addCallbacks(self._got_amount, self._failure)

    def _got_amount(self, amount):
        if amount < self._count[1]:
            d = MoveAmount(self._client, self.locked_box, self.secure_box,
                           lambda i: i.item_id in self._count[0], self._count[1] - amount).deferred
        elif amount > self._count[1]:
            d = MoveAmount(self._client, self.secure_box, self.locked_box,
                           lambda i: i.item_id in self._count[0], amount - self._count[1]).deferred
        else:
            self._check_counts()
            return
        d.addCallbacks(self._amount_moved, self._amount_moved)

    def _amount_moved(self, result):
        self._check_counts()

    def _finish(self):
        assert self.busy
        self.busy = False
        if self.scheduled:
            self._schedule()

    def on_container_item(self, item):
        if item.parent_serial == self.secure_box.serial:
            self._schedule()

def run(client):
    PrintMessages(client)
    AutoHide(client)
    return Janitor(client)

simple_run(run)
