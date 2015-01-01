# -*- coding: utf-8 -*-
"""The main entry point for server."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2015 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

import sys
from time import sleep

# noinspection PyProtectedMember
from .core.server import boot, loop, _store as server_store


if __name__ == "__main__":
    if "-R" in sys.argv:
        while True:
            if server_store.has("state"):
                break
            sleep(0.1)
    boot()
    loop()
