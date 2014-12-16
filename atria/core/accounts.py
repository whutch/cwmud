# -*- coding: utf-8 -*-
"""User accounts and client options."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

import re

from .entities import Entity, Attribute
from .requests import REQUESTS, Request
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

    # Other modules can add any reservations they need to this list.
    # Reserved account names should be all lowercase.
    RESERVED = ["new", "account", "help"]

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

    @classmethod
    def check_reserved(cls, name):
        """Check if an account name is reserved.

        :param str name: The account name to check
        :returns bool: True if the name is reserved, else False

        """
        return name in cls.RESERVED


# noinspection PyProtectedMember
@REQUESTS.register
class RequestNewAccountName(Request):

    """A request for a new account name."""

    initial_prompt = joins("Enter a new account name (account names must"
                           " be between", AccountName._min_len, "and",
                           AccountName._max_len, "characters in length"
                           " and contain only letters, numbers, or"
                           " underscore): ")
    repeat_prompt = "New account name: "
    confirm = Request.CONFIRM_YES
    confirm_prompt_yn = "'{data}', is that correct? (Y/N) "

    def _validate(self, data):
        try:
            new_name = AccountName._validate(data)
        except ValueError as exc:
            raise Request.ValidationFailed(*exc.args)
        if AccountName.check_reserved(new_name):
            raise Request.ValidationFailed("That account name is reserved.")
        if Account._store.has(new_name):
            raise Request.ValidationFailed("That account name is taken.")
        return new_name


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


# noinspection PyProtectedMember
@REQUESTS.register
class RequestNewAccountPassword(Request):

    """A request for a new account password."""

    initial_prompt = joins("Enter a new password (passwords must"
                           " be at least", AccountPassword._min_len,
                           "characters in length): ")
    repeat_prompt = "New password: "
    confirm = Request.CONFIRM_REPEAT

    def _validate(self, data):
        try:
            return AccountPassword._validate(data)
        except ValueError as exc:
            raise Request.ValidationFailed(*exc.args)
