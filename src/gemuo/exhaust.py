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

import os
import dbm

class ExhaustDatabase:
    """A file-based database of blocks whose resources are exhausted."""

    def __init__(self, path, duration=30):
        self._db = dbm.open(path, 'c')
        self.duration = duration

    def _key(self, x, y):
        return '%d,%d' % (x, y)

    def is_exhausted(self, x, y):
        key = self._key(x, y)
        try:
            t = self._db[key]
        except KeyError:
            return False
        now = os.times()[4]
        if now < float(t):
            return True
        else:
            # record is expired; delete it
            del self._db[key]
            return False

    def set_exhausted(self, x, y):
        key = self._key(x, y)
        now = os.times()[4]
        # this block is exhausted for 30 minutes
        self._db[key] = str(now + self.duration * 60)
        #self._db.sync()
