# -*- coding: utf-8 -*-
"""User accounts and client options."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

import re

from .entities import Entity, Attribute
from .utils.funcs import joins
from .opt.pickle import PickleStore


class Account(Entity):

    """A user account."""

    _store = PickleStore("accounts")
    _store_key = "name"
    _uid_code = "A"


@Account.register_attr("name")
class AccountName(Attribute):

    """An account name."""

    _min_len = 2
    _max_len = 16
    _valid_chars = re.compile(r"^[\w]+$")

    @classmethod
    def _validate(cls, new_value):
        if (not isinstance(new_value, str) or
                not cls._valid_chars.match(new_value)):
            raise ValueError("Account names can only contain alphanumeric"
                             " characters and underscore.")
        name_len = len(new_value)
        if name_len < cls._min_len or name_len > cls._max_len:
            raise ValueError(joins("Account names must be between",
                                   cls._min_len, "and", cls._max_len,
                                   "characters in length."))
        return new_value.lower()


@Account.register_attr("password")
class AccountPassword(Attribute):

    """An account password."""

    _min_len = 8

    @classmethod
    def _validate(cls, new_value):
        if not isinstance(new_value, str):
            raise TypeError("Account password must be a string.")
        if len(new_value) < 8:
            raise ValueError(joins("Account passwords must be at least",
                                   cls._min_len, "characters in length."))
        return new_value
