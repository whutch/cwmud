# -*- coding: utf-8 -*-
"""User accounts and client options."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from .entities import Entity
from .opt.pickle import PickleStore


class Account(Entity):

    """A user account."""

    _store = PickleStore("accounts")
    _store_key = "name"
    _uid_code = "A"
