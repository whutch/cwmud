# -*- coding: utf-8 -*-
"""The main entry point for server."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

import sys
from time import sleep

# noinspection PyProtectedMember
from .core.server import boot, loop, _SERVER_DATA


if __name__ == "__main__":
    if "-R" in sys.argv:
        while True:
            if _SERVER_DATA.has("state"):
                break
            sleep(0.1)
    boot()
    loop()
