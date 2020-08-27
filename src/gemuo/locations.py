#
#  GemUO
#
#  Copyright 2005-2020 Max Kellermann <max.kellermann@gmail.com>
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

# OSI Banks
BRITAIN_EAST_BANK = (1646,1598, 1646,1616, 1720,1580)
MINOC_BANK = (2493,541, 2513,561, 2500,570)
MOONGLOW_BANK = (4461,1150, 4481,1176, 4442,1200)

# UO Outlands Banks
PREVILIA_BANK = (1610,1509, 1620,1509, 1615,1509)

def is_rel_por(world):
    """Is this the Rel Por freeshard?"""
    return world.map_width == 7168 and world.map_height == 4096

def is_uo_outlands(world):
    """Is this the UO Outlands freeshard?"""
    return world.map_width == 7168 and world.map_height == 4096

def nearest_felucca_bank(world, position):
    if position.x < 1500:
        #BANK = BRITAIN_WEST_BANK
        # XXX implement
        return None
    elif position.x < 2000:
        return BRITAIN_EAST_BANK
    elif position.x > 3500:
        return MOONGLOW_BANK
    else:
        return MINOC_BANK

def nearest_bank(world, position):
    if is_uo_outlands(world):
        return PREVILIA_BANK
    else:
        return nearest_felucca_bank(world, position)


CENTER2 = (2260,480)
FORGES2 = (
    (2248,417),
    (2240,443),
    (2211,477),
    (2212,489),
)

MINOC_FORGES = (
    (2561,501),
    (2586,517),
    #(2599,475),
    (2468,555),
    (2469,555),
    (2468,557),
    (2469,557),
)

def nearest_forge(world, position):
    if is_rel_por(world):
        if position.y > 1470:
            # south of the mountain
            return (1317,1568)
        elif position.x >= 1250 and position.x <= 1360 and position.y >= 1280 and position.y <= 1330:
            # in cave
            return (1289,1311)
        elif position.x < 1270:
            return (1230,1327)
        else:
            # northern city end
            return (1317,1342)
    else:
        return None
