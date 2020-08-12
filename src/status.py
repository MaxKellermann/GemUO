#!/usr/bin/env python3

from twisted.internet import defer
from uo.skills import *
from uo.stats import *
from gemuo.simple import simple_run
from gemuo.engine.player import QuerySkills, QueryStats

def status(result, client):
    player = client.world.player
    print("Name:", "\t", player.name)
    if player.position is not None:
        print("Pos:", "\t", player.position)
    print("Serial: ", player.serial)
    print("Body:", "\t", player.body)
    print("Stats:", "\t", list(zip(("Str", "Dex", "Int"), player.stats)))
    if player.hits is not None:
        print("Hits:", "\t", player.hits.value, "/", player.hits.limit)
    if player.mana is not None:
        print("Mana:", "\t", player.mana.value, "/", player.mana.limit)
    if player.stamina is not None:
        prin(("Stam:", "\t", player.stamina.value, "/", player.stamina.limit)

    print("Skills:")
    skills = [x for x in iter(list(player.skills.values())) if x.base > 0]
    skills.sort(key=lambda x: x.base, reverse=True)
    total = 0
    for x in skills:
        print("\t", SKILL_NAMES[x.id], x.base / 10.0, LOCK_NAMES[x.lock])
        total += x.base
    print("\t", "Total", total / 10.0)

    print("Equipped:")
    for x in client.world.items_in(client.world.player):
        print("\t", x)
        pass

def run(client):
    d = defer.DeferredList((QuerySkills(client).deferred,
                            QueryStats(client).deferred))
    d.addCallback(status, client)
    return d

simple_run(run)
