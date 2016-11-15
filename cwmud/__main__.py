# -*- coding: utf-8 -*-
"""The main entry point for server."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from .nanny import start_listeners, start_nanny

if __name__ == "__main__":  # pragma: no cover
    start_listeners()
    start_nanny()
