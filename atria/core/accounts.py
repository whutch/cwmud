# -*- coding: utf-8 -*-
"""User accounts and client options."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2015 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

import re

from .entities import Entity, DataBlob, Attribute
from .logs import get_logger
from .menus import MENUS, Menu
from .requests import REQUESTS, Request, RequestString
from .shells import SHELLS
from .storage import STORES
from .utils.funcs import joins
from .opt.pickle import PickleStore


log = get_logger("accounts")


class Account(Entity):

    """A user account."""

    _store = STORES.register("accounts", PickleStore("accounts"))
    _store_key = "name"
    _uid_code = "A"

    def __repr__(self):
        if hasattr(self, "name") and self.name:
            return joins("Account<", self.name, ">", sep="")
        else:
            return "Account<unnamed>"


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


@Account.register_blob("options")
class AccountOptions(DataBlob):
    """A collection of account and client options."""
    pass


def authenticate_account(session, success=None, fail=None, account=None):
    """Perform a series of requests to authenticate a session's account.

    If given, either `success` or `fail` will be called with `session`
    and the account (if it exists) as positional arguments.

    If `account` is given, it will be used to authenticate against instead
    of the account already assigned to `session`. If not, and `session` has
    no account assigned, an account name will be requested first;
    otherwise only the password is requested.

    :param sessions._Session session: The session to authenticate
    :param callable success: Optional, a callback for successful authentication
    :param callable fail: Optional, a callback for failed authentication
    :param Account account: Optional, an account to authenticate against
    :returns: None

    """
    account = account if account else session.account
    if not account:
        # We need an account name first.
        def _check_account(_session, account_name):
            if not Account.exists(account_name):
                # Account not found, recursing with False as the account
                # will ensure that the password check fails.
                # noinspection PyTypeChecker
                authenticate_account(_session, fail, fail, account_name)
            else:
                _account = Account.load(account_name)
                authenticate_account(_session, success, fail, _account)
        session.request(RequestString, _check_account,
                        initial_prompt="Account name: ",
                        repeat_prompt="Account name: ")
    else:
        # Now we can request a password.
        def _check_password(_session, password):
            if not isinstance(account, Account):
                # They entered an account name and it didn't exist.
                if fail is not None:
                    fail(_session, account)
            else:
                # Check the given password against the account
                if password and password == account.password:
                    success(_session, account)
                else:
                    fail(_session, account)
        session.request(RequestString, _check_password,
                        initial_prompt="Password: ",
                        repeat_prompt="Password: ")


@MENUS.register
class AccountMenu(Menu):

    """An account menu."""

    title = "ACCOUNT MENU:"
    ordering = Menu.ORDER_BY_ALPHA


@AccountMenu.add_entry("L", "Enter lobby")
def _account_menu_enter_lobby(session):
    session.shell = SHELLS["ChatShell"]
    session.menu = None


@AccountMenu.add_entry("Q", "Quit")
def _account_menu_quit(session):
    session.close("Okay, goodbye!",
                  log_msg=joins(session, "has quit"))
