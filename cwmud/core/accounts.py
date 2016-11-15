# -*- coding: utf-8 -*-
"""User accounts and client options."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from functools import partial
import re
from weakref import WeakSet

from . import const
from .attributes import Attribute, DataBlob, Unset
from .entities import ENTITIES, Entity
from .events import EVENTS
from .logs import get_logger
from .menus import Menu, MENUS
from .players import Player, create_player
from .requests import Request, REQUESTS, RequestString
from .shells import SHELLS
from .utils.funcs import check_hash, generate_hash, joins


log = get_logger("accounts")


@ENTITIES.register
class Account(Entity):

    """A user account."""

    _uid_code = "A"

    type = "account"

    def __init__(self, data=None, active=False, savable=True):
        super().__init__(data, active, savable)
        self._sessions = WeakSet()

    def __repr__(self):
        if hasattr(self, "name") and self.name:
            return joins("Account<", self.name, ">", sep="")
        else:
            return "Account<(unnamed)>"

    def login(self, session):
        """Process an account login for a session.

        :param sessions.Session session: The session logging in
        :returns None:

        """
        with EVENTS.fire("account_login", session, self):
            log.info("%s has logged in to %s.", session, self)
            session.send("\nMOTD will go here!")
            if session not in self._sessions:
                self._sessions.add(session)
            if not self.active:
                self.active = True

    def logout(self, session):
        """Process an account logout for a session.

        :param sessions.Session session: The session logging out
        :returns None:

        """
        with EVENTS.fire("account_logout", session, self):
            log.info("%s has logged out of %s.", session, self)
            if session in self._sessions:
                self._sessions.remove(session)
            if not self._sessions:
                self.active = False


# noinspection PyProtectedMember
@Account.register_attr("email")
class AccountEmail(Attribute):

    """An account's e-mail address."""

    # There's a jillion regexes and RFCs for matching emails, I don't
    # really care about validating them perfectly, I just want to check
    # if they are really obviously not valid.
    _pattern = re.compile(r"^[\w.%+-]+@[\w.%+-]+\.[a-zA-Z]{2,4}$")

    @classmethod
    def validate(cls, entity, new_value):
        if (not isinstance(new_value, str) or
                not cls._pattern.match(new_value)):
            raise ValueError("Invalid email address.")
        new_value = new_value.lower()
        if Account._store.has(new_value):
            raise Request.ValidationFailed("That email is already in use.")
        return new_value


# noinspection PyProtectedMember
@REQUESTS.register
class RequestNewAccountEmail(Request):

    """A request for a new account email."""

    initial_prompt = joins("Enter an email address for this account (emails"
                           " are used for account login and recovery purposes,"
                           " by default no other communication will be sent"
                           " to your email): ")
    repeat_prompt = "New account email: "
    confirm = Request.CONFIRM_REPEAT

    def _validate(self, data):
        try:
            new_email = AccountEmail.validate(None, data)
        except ValueError as exc:
            raise Request.ValidationFailed(*exc.args)
        return new_email


@Account.register_attr("name")
class AccountName(Attribute):

    """An account's display name."""

    _min_len = 2
    _max_len = 16
    _valid_chars = re.compile(r"^[\w]+$")

    # Other modules can add any reservations they need to this list.
    # Reserved account names should be all lowercase.
    RESERVED = []

    @classmethod
    def validate(cls, entity, new_value):
        if (not isinstance(new_value, str) or
                not cls._valid_chars.match(new_value)):
            raise ValueError("Account names can only contain alphanumeric"
                             " characters and underscore.")
        name_len = len(new_value)
        if name_len < cls._min_len or name_len > cls._max_len:
            raise ValueError(joins("Account names must be between",
                                   cls._min_len, "and", cls._max_len,
                                   "characters in length."))
        new_value = new_value.lower()
        if AccountName.check_reserved(new_value):
            raise ValueError("That account name is reserved.")
        if Account.find(name=new_value):
            raise ValueError("That account name is already in use.")
        return new_value

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
            new_name = AccountName.validate(None, data)
        except ValueError as exc:
            raise Request.ValidationFailed(*exc.args)
        return new_name


@Account.register_attr("password")
class AccountPassword(Attribute):

    """An account password."""

    _min_len = 8

    @classmethod
    def validate(cls, entity, new_value):
        if not isinstance(new_value, str):
            raise TypeError("Account password must be a string.")
        if len(new_value) < 8:
            raise ValueError(joins("Account passwords must be at least",
                                   cls._min_len, "characters in length."))
        return new_value

    @classmethod
    def finalize(cls, entity, new_value):
        return generate_hash(new_value)


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
            return AccountPassword.validate(None, data)
        except ValueError as exc:
            raise Request.ValidationFailed(*exc.args)


@Account.register_attr("trust")
class AccountTrust(Attribute):

    """An account's trust level."""

    _default = const.TRUST_PLAYER

    @classmethod
    def validate(cls, entity, new_value):
        if not isinstance(new_value, int):
            raise TypeError("Account trust must be an integer.")
        return new_value


@Account.register_blob("options")
class AccountOptions(DataBlob):
    """A collection of account and client options."""


@AccountOptions.register_attr("reader")
class AccountOptionsReader(Attribute):

    """An account option for using a screen reader."""

    @classmethod
    def validate(cls, entity, new_value):
        if not isinstance(new_value, bool):
            raise TypeError("The reader option must be either True or False.")
        return new_value


# noinspection PyProtectedMember
@REQUESTS.register
class RequestAccountOptionsReader(Request):

    """A request for the reader account option."""

    repeat_prompt = "Do you use a screen reader? (Y/N) "

    def _validate(self, data):
        if isinstance(data, str):
            if "yes".startswith(data.lower()):
                return True
            elif "no".startswith(data.lower()):
                return False
        raise Request.ValidationFailed("Please enter 'yes' or 'no'.")


@AccountOptions.register_attr("color")
class AccountOptionsColor(Attribute):

    """An account option for using color."""

    @classmethod
    def validate(cls, entity, new_value):
        if not isinstance(new_value, bool):
            raise TypeError("The color option must be either True or False.")
        return new_value


# noinspection PyProtectedMember
@REQUESTS.register
class RequestAccountOptionsColor(Request):

    """A request for the color account option."""

    repeat_prompt = "Do you wish to use color? (Y/N) "

    def _validate(self, data):
        if isinstance(data, str):
            if "yes".startswith(data.lower()):
                return True
            elif "no".startswith(data.lower()):
                return False
        raise Request.ValidationFailed("Please enter 'yes' or 'no'.")


@AccountOptions.register_attr("width")
class AccountOptionsWidth(Attribute):

    """An account option for screen width."""

    @classmethod
    def validate(cls, entity, new_value):
        if not isinstance(new_value, int):
            raise TypeError("The width option must be an integer.")
        return new_value


# noinspection PyProtectedMember
@REQUESTS.register
class RequestAccountOptionsWidth(Request):

    """A request for the width account option."""

    repeat_prompt = "Enter your screen width: "

    def _validate(self, data):
        try:
            value = int(data)
            if value < 1:
                raise ValueError
            return value
        except (TypeError, ValueError):
            raise Request.ValidationFailed("Please enter a number greater "
                                           " than zero.")


# noinspection PyUnresolvedReferences
def create_account(session, callback, account=None):
    """Perform a series of requests to create a new account.

    :param sessions.Session session: The session creating an account
    :param callable callback: A callback for when the account is created
    :param Account account: The account in the process of being created
    :returns None:

    """
    if not account:
        account = Account()
        account._savable = False
    if not account.email:
        def _set_email(_session, new_email):
            account.email = new_email
            create_account(_session, callback, account)
        session.request(RequestNewAccountEmail, _set_email)
    elif not account.name:
        def _set_name(_session, new_name):
            account.name = new_name
            create_account(_session, callback, account)
        session.request(RequestNewAccountName, _set_name)
    elif not account.password:
        def _set_password(_session, new_password):
            account.password = new_password
            create_account(_session, callback, account)
        session.request(RequestNewAccountPassword, _set_password)
    elif account.options.reader is Unset:
        def _set_reader_option(_session, option):
            account.options.reader = option
            # They don't need color if they are using a screen reader.
            if option is True:
                account.options.color = False
            create_account(_session, callback, account)
        session.request(RequestAccountOptionsReader, _set_reader_option)
    elif account.options.color is Unset:
        def _set_color_option(_session, option):
            account.options.color = option
            create_account(_session, callback, account)
        session.request(RequestAccountOptionsColor, _set_color_option)
    else:
        account._savable = True
        callback(session, account)


def authenticate_account(session, success=None, fail=None, account=None):
    """Perform a series of requests to authenticate a session's account.

    If given, either `success` or `fail` will be called with `session`
    and the account (if it exists) as positional arguments.

    If `account` is given, it will be used to authenticate against instead
    of the account already assigned to `session`.  If not, and `session` has
    no account assigned, an account name will be requested first;
    otherwise only the password is requested.

    :param sessions.Session session: The session to authenticate
    :param callable success: Optional, a callback for successful authentication
    :param callable fail: Optional, a callback for failed authentication
    :param Account account: Optional, an account to authenticate against
    :returns None:

    """
    account = account if account else session.account
    if not account:
        # We need the account's email first.
        def _check_account(_session, account_email):
            _account = Account.get(email=account_email)
            if not _account:
                # Account not found, recursing with the account email string
                # as the account will ensure that the password check fails.
                # noinspection PyTypeChecker
                authenticate_account(_session, fail, fail, account_email)
            else:
                authenticate_account(_session, success, fail, _account)
        session.request(RequestString, _check_account,
                        initial_prompt="Account email: ",
                        repeat_prompt="Account email: ")
    else:
        # Now we can request a password.
        def _check_password(_session, password):
            if not isinstance(account, Account):
                # They entered an account email and it didn't exist.
                if fail is not None:
                    fail(_session, account)
            else:
                # Check the given password against the account.
                if password and check_hash(password, account.password):
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

    def _init(self):
        """Add account-specific entries to the menu."""
        account = self.session.account
        if not account:
            log.warning("AccountMenu assigned to session with no account!")
            return
        # Add entries for the account's characters.
        chars = Player.find_relations(account=account)
        for n, char in enumerate(sorted(chars, key=lambda c: c.name), 1):
            self.add_entry(str(n), char.name,
                           partial(_account_menu_select_char, char=char))


def _account_menu_select_char(session, char=None):
    if not char:
        return
    if not char.room:
        from .world import Room
        start_room = Room.get(x=0, y=0, z=0)
        if start_room:
            char.room = start_room
    session.shell = SHELLS["CharacterShell"]
    if char.session and char.session is not session:
        session.send("^RConnecting to active character. Previous connection"
                     " from {}.^~".format(char.session.host))
        char.session.char = None
        char.session.close("^RThis character has been logged in from another"
                           " session. Good bye.^~",
                           log_msg=("{} logged in from {}, closing {}."
                                    .format(char, session, char.session)))
        char.session.poll(output_only=True)
    else:
        session.send("Welcome", char.name, "!\n")
        char.resume()
    session.char = char
    session.menu = None


@AccountMenu.add_entry("Q", "Quit")
def _account_menu_quit(session):
    session.close("Okay, goodbye!",
                  log_msg=joins(session, "has quit."))


@AccountMenu.add_entry("C", "Create character")
def _account_menu_create_character(session):
    def _callback(_session, player):
        # Save the player before it gets garbage collected.
        player.save()
        # Build a new menu with an entry for the character.
        _session.menu = AccountMenu
    create_player(session, _callback)
