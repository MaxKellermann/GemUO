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

from uo.multis import multi_passable_at
from gemuo.entity import Item

class BridgeMap:
    """A wrapper for the map class which allows PathFindWalk to walk
    over bridges.  We havn't implemented walking over statics properly
    yet, but this hack is good enough for now."""

    def __init__(self, map):
        self.map = map

    def is_passable(self, x, y, z):
        if x >= 1376 and x <= 1398 and y >= 1745 and y <= 1753: return True
        if x >= 1517 and x <= 1530 and y >= 1671 and y <= 1674: return True
        if x >= 2528 and x <= 2550 and y >= 499 and y <= 502: return True
        if x >= 2528 and x <= 2550 and y >= 499 and y <= 502: return True

        # brit mauer
        if x >= 1419 and x <= 1421 and y >= 1633 and y <= 1638: return True
        if x >= 1462 and x <= 1466 and y >= 1639 and y <= 1643: return True
        if x >= 1468 and x <= 1472 and y >= 1639 and y <= 1643: return True
        if x >= 1478 and x <= 1482 and y >= 1639 and y <= 1643: return True
        if x >= 1480 and x <= 1484 and y >= 1639 and y <= 1643: return True

        # Rel Por city walls
        if x >= 1244 and x <= 1248 and y >= 1428 and y <= 1433: return True
        if x >= 1374 and x <= 1380 and y >= 1350 and y <= 1353: return True
        if x >= 1191 and x <= 1198 and y >= 1335 and y <= 1338: return True

        # Bridge east of Rel Por city wall
        if x >= 1401 and x <= 1415 and y >= 1344 and y <= 1346: return True

        # RelPor Healer
        if (x == 1281 or x == 1282) and y == 1335: return True
        if x >= 1279 and x <= 1285 and y >= 1325 and y <= 1334: return True

        return self.map.is_passable(x, y, z)

    def __getattr__(self, name):
        x = getattr(self.map, name)
        setattr(self, name, x)
        return x

class WorldMap:
    """A wrapper for the map class which considers dynamic obstacles
    (items, mobiles)."""

    def __init__(self, map, world):
        self.map = map
        self.world = world

    def _is_passable(self, world, entity):
        if isinstance(entity, Item):
            if entity.item_id in (0x1BC3, # teleporter
                                  0xF6C, # moongate
                                  ):
                # don't step through moongates
                return False
            else:
                return self.map.tile_data.item_passable(entity.item_id & 0x3fff)
        else:
            if entity.serial == world.player.serial:
                return True
            else:
                # never step over other mobiles
                return False

    def is_passable(self, x, y, z):
        world = self.world
        try:
            world.lock()
            for e in world.iter_entities_at(x, y):
                if not self._is_passable(world, e):
                    return False

            for i in world.iter_multis():
                if i.position is not None:
                    if z is not None and i.position.z is not None:
                        dz = z - i.position.z
                    else:
                        dz = 0

                    if not multi_passable_at(i.item_id, x - i.position.x,
                                             y - i.position.y, dz):
                        return False
        finally:
            world.unlock()

        return self.map.is_passable(x, y, z)

    def __getattr__(self, name):
        x = getattr(self.map, name)
        setattr(self, name, x)
        return x

class CacheMap:
    """A wrapper for the map class which caches the is_passable()
    results."""

    def __init__(self, map):
        self.__map = map
        self.__cache = dict()

    def flush_cache(self):
        self.__map.flush_cache()
        self.__cache.clear()

    def is_passable(self, x, y, z):
        if z is None: z = 0
        k = (x << 20) | (y << 4) | (z + 8)
        if k in self.__cache:
            return self.__cache[k]

        result = self.__map.is_passable(x, y, z)
        self.__cache[k] = result
        return result

    def __getattr__(self, name):
        x = getattr(self.__map, name)
        setattr(self, name, x)
        return x
