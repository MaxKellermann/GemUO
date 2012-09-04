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

class Resource:
    def __init__(self, x, y, z, item_id, hue):
        self.x, self.y, self.z = x, y, z
        self.item_id, self.hue = item_id, hue

def iter_statics_in_block(map, block_x, block_y, ids):
    block = map.statics.load_block(block_x, block_y)
    if block is None:
        return

    for item_id, x, y, z, hue in block:
        if item_id in ids:
            yield Resource(block_x * 8 + x, block_y * 8 + y, z, item_id, hue)

def iter_static_near(map, x, y, max_distance, ids):
    block_min_x = (x - max_distance) / 8
    block_max_x = (x + max_distance) / 8
    block_min_y = (y - max_distance) / 8
    block_may_y = (y + max_distance) / 8

    for block_x in range(block_min_x, block_max_x):
        for block_y in range(block_min_y, block_may_y):
            for r in iter_statics_in_block(map, block_x, block_y, ids):
                distance = abs(r.x - x) + abs(r.y - y)
                if distance <= max_distance:
                    yield r

def find_static_near(map, x, y, max_distance, ids):
    for r in iter_static_near(map, x, y, max_distance, ids):
        return r
    return None
