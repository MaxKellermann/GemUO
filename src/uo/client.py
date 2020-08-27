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

import struct
from twisted.internet.protocol import Protocol
from uo.error import ProtocolError
from uo.serialize import packet_lengths, PacketReader
from uo.compression import Decompress

class UOProtocol(Protocol):
    def __init__(self, seed=42, decompress=False):
        self.__seed = seed
        self.__decompress = decompress

    def connectionMade(self):
        Protocol.connectionMade(self)

        self.transport.setTcpNoDelay(False)

        self.transport.write(struct.pack('>I', self.__seed))
        self._input = b''

        self._decompress = None
        if self.__decompress:
            self._decompress = Decompress()

    def connectionLost(self, reason):
        Protocol.connectionLost(self, reason)
        print(("connectionLost", repr(reason)))

    def _packet_from_buffer(self):
        if not self._input:
            return None

        cmd = self._input[0]
        l = packet_lengths[cmd]
        if l == 0xffff:
            raise ProtocolError("Unsupported packet 0x%x" % cmd)
        if l == 0:
            if len(self._input) < 3: return None
            l = struct.unpack('>H', self._input[1:3])[0]
            if l < 3 or l > 0x8000:
                raise ProtocolError("Malformed packet")
            if len(self._input) < l: return None
            x, self._input = self._input[3:l], self._input[l:]
        else:
            if len(self._input) < l: return None
            x, self._input = self._input[1:l], self._input[l:]
        return PacketReader(cmd, x)

    def on_packet(self, packet):
        self.handler(packet)

    def dataReceived(self, data):
        if self._decompress:
            data = self._decompress.decompress(data)

        self._input += data

        while True:
            packet = self._packet_from_buffer()
            if packet is None: break

            self.on_packet(packet)

    def send(self, data):
        self.transport.write(data)
