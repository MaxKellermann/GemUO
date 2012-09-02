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

# Loader for the UO client cliloc files.

import os
import struct
import gemuo.config

global_cliloc = None

def load_cliloc_file(path):
    result = dict()

    with file(path) as f:
        f.read(6)

        while True:
            data = f.read(7)
            if len(data) != 7: break

            number, length = struct.unpack('<IxH', data)
            text = f.read(length)
            if len(text) != length: break

            text = text.decode('utf-8', 'ignore')
            result[number] = text

    return result

def lookup_cliloc(id):
    global global_cliloc
    if global_cliloc is None:
        data_path = gemuo.config.get_data_path()
        if data_path is not None:
            path = os.path.join(data_path, 'Cliloc.enu')
            try:
                global_cliloc = load_cliloc_file(path)
            except:
                global_cliloc = dict()
        else:
            global_cliloc = dict()

    if id in global_cliloc:
        return global_cliloc[id] + ' [%#x]' % id
    else:
        return '%#x' % id
