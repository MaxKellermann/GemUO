#!/usr/bin/env python3
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

from twisted.internet import reactor
from uo.entity import *
from gemuo.entity import Item
from gemuo.simple import simple_run
from gemuo.error import *
from gemuo.defer import deferred_find_item_in, deferred_find_item_in_backpack
from gemuo.engine.messages import PrintMessages
from gemuo.engine.restock import drop_into

def run(client):
    PrintMessages(client)

    world = client.world
    for e in world.iter_entities_at(world.player.position.x, world.player.position.y-1):
        print(e)

simple_run(run)
