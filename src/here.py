#!/usr/bin/python

import gemuo.config
from gemuo.data import TileCache
from gemuo.simple import simple_run
from gemuo.engine.player import QuerySkills, QueryStats

tc = TileCache(gemuo.config.require_data_path())
m = tc.get_map(0)

def dump_at(x, y, world):
    print
    print "At %d,%d:" % (x, y)
    print "land: id=%#x h=%d flags=%#x" % (m.land_tile_id(x, y),
                                           m.land_tile_height(x, y),
                                           m.land_tile_flags(x, y))

    for id, z, hue in m.statics_at(x, y):
        print "static: id=%#x h=%d flags=%#x hue=%#x" % (id, z, tc._tile_data.item_flags[id], hue)

    for e in world.iter_entities_at(x, y):
        print "entity: %s" % e

def run(client):
    player = client.world.player
    print "Name:", "\t", player.name
    if player.position is not None:
        print "Pos:", "\t", player.position
    print "Serial: ", player.serial
    print "Body:", "\t", player.body

    print "Equipped:"
    for x in client.world.items_in(client.world.player):
        print "\t", x
        pass

    if player.position is not None:
        x, y = player.position.x, player.position.y
        dump_at(x, y, client.world)
        dump_at(x, y-1, client.world)
        dump_at(x-1, y, client.world)
        dump_at(x+1, y, client.world)
        dump_at(x+1, y+1, client.world)

simple_run(run)
