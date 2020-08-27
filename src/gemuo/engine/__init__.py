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

from twisted.internet.defer import Deferred

class Engine:
    def __init__(self, client):
        assert client is not None

        self._client = client
        self._client.add_engine(self)
        self.deferred = Deferred(canceller=self.__cancel)

    def _disconnect(self):
        if self._client is not None:
            self._client._client.transport.loseConnection()
            self._client = None

    def _signal(self, name, *args, **keywords):
        assert self._client is not None

        self._client.signal(name, *args, **keywords)

    def __stop(self):
        if self._client is not None:
            self._client.remove_engine(self)
            self._client = None

    def _success(self, result=None):
        self.__stop()
        self.deferred.callback(result)

    def _failure(self, fail='Engine failed'):
        self.__stop()
        self.deferred.errback(fail)

    def abort(self):
        """Aborts this engine, does not emit a signal."""
        self.__stop()

    def __cancel(self, d):
        self.abort()
