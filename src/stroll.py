#!/usr/bin/python

import gemuo.config
from gemuo.simple import simple_run
from gemuo.engine.messages import PrintMessages
from gemuo.engine.guards import Guards
from gemuo.data import TileCache
from gemuo.map import BridgeMap, WorldMap, CacheMap
from gemuo.engine.stroll import StrollWestBritain

def run(client):
    PrintMessages(client)
    Guards(client)

    tc = TileCache(gemuo.config.require_data_path())
    m = CacheMap(WorldMap(BridgeMap(tc.get_map(0)), client.world))

    return StrollWestBritain(client, m)

simple_run(run)
