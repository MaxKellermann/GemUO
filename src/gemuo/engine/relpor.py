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

import re
from twisted.python import log
import uo.packets as p
from gemuo.engine import Engine

tilepic_re = re.compile(r'\{ tilepic \d+ \d+ (\d+) \}')

class RelPorCaptcha(Engine):
    """Responds to the captcha gumps on the Rel Por freeshard."""

    def _on_captcha(self, packet):
        tiles = []

        total = 0
        for m in tilepic_re.findall(packet.layout):
            value = int(m)
            total += value
            tiles.append(value)

        log.msg("Captcha: " + ','.join(map(hex, tiles)))
        if len(tiles) == 0: return

        # see which tile id deviates the most
        avg = total // len(tiles)
        d = [abs(avg - value) for value in tiles]
        m = max(list(zip(d, list(range(len(d))))), key=lambda value: value[0])

        # pick this tile
        response = m[1]
        log.msg("Captcha response: %#x" % tiles[response])

        # and send the gump response
        self._client.send(p.GumpResponse(serial=packet.serial,
                                         gump_id=packet.gump_id,
                                         button_id=1,
                                         switches=[response]))

    def on_packet(self, packet):
        if isinstance(packet, p.DisplayGumpPacked) and \
               len(packet.text) == 1 and \
               'Which of these things is not like the others' in packet.text[0]:
            self._on_captcha(packet)
