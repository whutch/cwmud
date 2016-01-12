# -*- coding: utf-8 -*-
"""The main entry point for server."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from .nanny import start_nanny

if __name__ == "__main__":  # pragma: no cover
    start_nanny()
