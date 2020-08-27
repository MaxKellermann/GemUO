#!/usr/bin/python
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

from twisted.internet import reactor
from uo.entity import *
from gemuo.simple import simple_run
from gemuo.defer import deferred_find_item_in_backpack
from gemuo.error import *
from gemuo.engine import Engine
from gemuo.engine.messages import PrintMessages
from gemuo.engine.items import UseAndTarget
from gemuo.defer import deferred_find_player_item
from gemuo.engine.relpor import RelPorCaptcha

class MakeBoardsRelpor(Engine):

    def __init__(self, client):
        Engine.__init__(self, client)

        self._find_axe()
       

    def _find_axe(self):
        d = deferred_find_player_item(self._client, lambda x: x.item_id in ITEMS_AXE)
        d.addCallbacks(self._found_axe, self._failure)
                        

    def _found_axe(self, axe):
        if axe is None:
            print("No axe")
            self.failure()
            return
              
        self.axe = axe
        self._find_logs()


    def _find_logs(self):
        d = deferred_find_item_in_backpack(self._client, lambda x: x.item_id in ITEMS_LOGS)
        d.addCallbacks(self._found_logs, self._failure)


    def _found_logs(self, logs):
        if logs is None:
            print("No logs")
            self.failure()
            return

        self.logs = logs
        self._make_boards()


    def _make_boards(self):
        d = UseAndTarget(self._client, self.axe, self.logs).deferred
        d.addCallbacks(self._done, self._failure)

    def _done(self, result):
        reactor.callLater(1, self._success)

#def run(client):
#    PrintMessages(client)
#    RelPorCaptcha(client)

#    return MakeBoards_on_Relpor(client)

#simple_run(run)
