#!/usr/bin/env python3#
#
#  GemUO
#
#  (c) 2005-2010 Max Kellermann <max@duempel.org>
#                Kai Sassmannshausen <kai@sassie.org>
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

import uo.packets as p
import gemuo.config
from gemuo.simple import simple_run
from gemuo.data import TileCache
from gemuo.map import BridgeMap, WorldMap, CacheMap
from gemuo.engine.death import AutoResurrect

def run(client):
    tc = TileCache(gemuo.config.require_data_path())
    m = CacheMap(WorldMap(BridgeMap(tc.get_map(0)), client.world))

    return AutoResurrect(client, m)

simple_run(run)
