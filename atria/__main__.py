# -*- coding: utf-8 -*-
"""The main entry point for server."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from .core.server import boot, loop


if __name__ == "__main__":
    boot()
    loop()
