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

from twisted.python import log
from twisted.internet import reactor
import uo.packets as p
from uo.entity import *
from gemuo.engine import Engine
from gemuo.target import Target
from gemuo.error import *
from gemuo.defer import deferred_find_player_item
from gemuo.engine.items import OpenContainer, UseAndTarget

class Mine(Engine):
    def __init__(self, client, map, mountain, exhaust_db):
        Engine.__init__(self, client)

        self.exhaust_db = exhaust_db
        self.exhausted = False
        self.tries = 5

        self.mountain = mountain

        self.timeout_call = reactor.callLater(8, self._timeout)
        self._begin()

    def _timeout(self):
        log.msg("Mining timeout")
        self.timeout_call = None
        self.exhausted = True
        self.exhaust_db.set_exhausted(self.mountain.x // 8, self.mountain.y // 8)

    def _cancel_timeout(self):
        if self.timeout_call is None: return
        self.timeout_call.cancel()
        self.timeout_call = None

    def _begin(self):
        player = self._client.world.player
        if player.mass_remaining() < 25:
            self._success()
            return

        d = deferred_find_player_item(self._client, lambda x: x.item_id in ITEMS_MINING_TOOLS)
        d.addCallbacks(self._found_tool, self._failure)

    def _found_tool(self, tool):
        d = UseAndTarget(self._client, tool, self.mountain).deferred
        d.addCallbacks(self._mined, self._target_failure)

    def _target_failure(self, fail):
        if self.exhausted:
            self._success()
            return

        self.tries -= 1
        if self.tries > 0:
            self._begin()
        else:
            self._failure(fail)

    def _mined(self, result):
        self.tries = 5
        if self.exhausted:
            self._success()
        else:
            reactor.callLater(1, self._begin)

    def _on_system_message(self, text):
        if 'no metal here' in text or \
               'Target cannot be seen' in text:
            self.exhausted = True
            self.exhaust_db.set_exhausted(self.mountain.x // 8, self.mountain.y // 8)
        elif 'worn out your tool' in text:
            self.exhausted = True
        elif 'put it into your backpack' in text or \
                 'fail to find any useable ore' in text:
            self._cancel_timeout()

    def on_packet(self, packet):
        if isinstance(packet, p.AsciiMessage):
            if packet.type == 0 and packet.serial == 0xffffffff and \
               packet.name == 'System':
                self._on_system_message(packet.text)

    def on_localized_system_message(self, text):
        if text in (0x7ad00, # no metal here
                    0x7a867, # can't mine that
                    0x7a2de, # too far away
                    0x7a20d, # cannot be seen
                    ):
            self.exhausted = True
            self.exhaust_db.set_exhausted(self.mountain.x // 8, self.mountain.y // 8)
        elif text == 0xfee46: # worn out your tool
            self.exhausted = True
        elif text in (0xf5de0, 0xf5de1, 0xf5de2, 0xf5de3, 0xf5de4, 0xf5de5, 0xf5de6, 0xf5de7, # put it in your backpack
                      0x7ad03, # fail to find any useable ore
                      ):
            self._cancel_timeout()

    def on_combatant(self, serial):
        if serial != 0:
            self.exhausted = True

    def on_death(self):
        self.exhausted = True

class MergeOre(Engine):
    def __init__(self, client, container=None):
        Engine.__init__(self, client)
        self.__failed = False
        self.__tries = 10
        self.container = container

        d = OpenContainer(client, self.container).deferred
        d.addCallbacks(self._more, self._failure)

    def _more(self, *args):
        self.__tries -= 1
        if self.__tries < 0:
            self._success()
            return

        if self.__failed:
            self._failure(self.__failed)
            return

        ores = find_two_same_hue(list(filter(is_ore, self._client.world.items_in(self.container))))
        if ores is None:
            self._success()
            return

        log.msg("MergeOre")
        d = UseAndTarget(self._client, ores[0], ores[1]).deferred
        d.addCallbacks(self._merged, self._failure)

    def _merged(self, result):
        reactor.callLater(1, self._more)

    def on_localized_system_message(self, text):
        if text == 0x7a8da: # weight is too great to combine in a container
            self.__failed = hex(text)
