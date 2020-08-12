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

import re
from twisted.python import log
import uo.packets as p
from gemuo.entity import Position
from gemuo.engine import Engine
from gemuo.engine.walk import PathFindWalkNear

resurrect_gump_re = re.compile(r'xmfhtmlgump.*\s1011022\s.*xmfhtmlgump.*\s10110\d\d\s')

class AcceptResurrect(Engine):
    def __init__(self, client):
        Engine.__init__(self, client)

        if not self._client.is_dead():
            self._success()
            return

        self._client.send(p.WarMode(True))

    def on_packet(self, packet):
        if isinstance(packet, p.Menu):
            if packet.title == "It is possible for you to be resurrected now. Do you wish to try?":
                log.msg("Accepting resurrect by player")
                self._client.send(p.MenuResponse(packet.dialog_serial, 0o1))
        elif isinstance(packet, p.DisplayGumpPacked) and resurrect_gump_re.search(packet.layout):
            # the NPC healer resurrection gump
            log.msg("Accepting resurrect by NPC healer")
            self._client.send(p.GumpResponse(serial=packet.serial,
                                             gump_id=packet.gump_id,
                                             button_id=1))

    def check_player(self, m):
        if m != self._client.world.player: return
        if not m.is_dead():
            log.msg("Resurrected")
            self._signal('on_resurrect')
            self._success()

    on_mobile_status = check_player
    on_mobile_update = check_player

class AutoResurrect(Engine):
    def __init__(self, client, map):
        Engine.__init__(self, client)
        self.map = map

        self.accept = None
        self.walk = None

        if client.is_dead():
            self.on_death()

    def on_death(self):
        log.msg("Death")

        if self.accept is None:
            self.accept = AcceptResurrect(self._client)
            self.accept.deferred.addCallbacks(self._resurrected, self._failure)

        self.tries = 5
        self._walk_to_healer()

    def _walk_to_healer(self):
        if self.walk is not None: return
        self.walk = PathFindWalkNear(self._client, self.map,
                                     Position(1281, 1326), 3)
        self.walk.deferred.addCallbacks(self._walked, self._walk_failed)

    def _resurrected(self, *args):
        self.accept = None

        if self.walk is not None:
            self.walk.abort()
            self.walk = None

    def _walked(self, *args):
        self.walk = None

    def _walk_failed(self, failure):
        log.msg(failure)
        self.walk = None

        self.tries -= 1
        if self.tries > 0:
            self._walk_to_healer()
