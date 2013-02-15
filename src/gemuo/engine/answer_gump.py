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


from twisted.python import log
import uo.packets as p
from gemuo.engine import Engine


class ShowGump(Engine):
    def __init__(self, client):
        Engine.__init__(self, client)


    def on_packet(self, packet):
        if isinstance(packet, p.DisplayGumpPacked):
            self.gserial = packet.serial
            self.gid = packet.gump_id
            print self.gserial
            print self.gid


class AnswerGump(Engine):
    def __init__(self, client):
        Engine.__init__(self, client)


    def answer_gump(self, packet):
        self._client.send(p.GumpResponse(packet.serial, packet.gump_id, 0x77, []))


    def on_packet(self, packet):
        if isinstance(packet, p.DisplayGumpPacked):
            self.answer_gump(packet)


