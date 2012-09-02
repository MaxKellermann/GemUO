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

BRITAIN_EAST_BANK = (1646,1598, 1646,1616, 1720,1580)
MINOC_BANK = (2493,541, 2513,561, 2500,570)
MOONGLOW_BANK = (4461,1150, 4481,1176, 4442,1200)

def is_rel_por(world):
    """Is this the RelPor freeshard?"""
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
    if is_rel_por(world):
        return (1335,1370, 1349,1381, 1281,1395)
    else:
        return nearest_felucca_bank(world, position)
