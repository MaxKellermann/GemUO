#!/usr/bin/env python3#
#
#  GemUO
#
#  Copyright 2005-2020 Max Kellermann <max.kellermann@gmail.com>
#                Kai Sassmannshausen <kai@sassie.org>
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

from gemuo.simple import simple_run
from gemuo.engine.death import AcceptResurrect
import uo.packets as p

def run(client):
    return AcceptResurrect(client)

simple_run(run)
