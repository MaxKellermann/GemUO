GemUO
=====

What is GemUO?
--------------

GemUO is an Ultima Online client written in the Python programming
language.  It was written with unattended macroing in mind; it should
be possible to write complex bots for training skills, harvesting
resources or even fighting.


Installation
------------

GemUO is being developed on Linux, but it probably runs on Windows,
too.  You need:

- Python 3.7 or newer
- `Twisted <https://twistedmatrix.com/trac/>`__

On Debian/Ubuntu and similar Linux distributions, the following
command will install all required packages::

 sudo apt-get install python3 python3-twisted

To install GemUO, clone the git repository::

 git clone https://github.com/MaxKellermann/GemUO

Some features (e.g. path finding) require the original UO client (or
rather: its map files, i.e. ``map0.mul`` etc.).  To tell GemUO where
to find them, create the file ``~/.gemuo/config`` or
``/etc/gemuo/config`` and type::

 [uo]
 path = /opt/uo


Running
-------

Type::

 python src/hiding.py the.server.com 2593 username password CharName

This connects to the specified shard, and trains the Hiding skill.
There are other example macros.

It is recommended to run GemUO with `uoproxy
<https://github.com/MaxKellermann/uoproxy/>`__ so you can watch the
scripts while they run.


Documentation
-------------

So far, there has been little time to write documentation on the code.
This project is aimed at hackers who can read the source.


Contributing
------------

Contributions to GemUO are welcome.  Send bug reports and pull
requests to GitHub: https://github.com/MaxKellermann/GemUO


Legal
-----

Copyright 2005-2020 Max Kellermann <max.kellermann@gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; version 2 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
