# -*- coding: utf-8 -*-
"""Characters, the base of life in the MUD."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2015 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

import re

from .commands import COMMANDS, Command
from .entities import ENTITIES, Entity, Attribute, Unset
from .logs import get_logger
from .requests import REQUESTS, Request
from .shells import SHELLS, STATES, Shell
from .storage import STORES
from .utils.funcs import joins
from .opt.pickle import PickleStore


log = get_logger("characters")


@ENTITIES.register
class Character(Entity):

    """A MUD character. So full of potential."""

    _store = STORES.register("characters", PickleStore("characters"))
    _store_key = "name"
    _uid_code = "C"

    def __repr__(self):
        if hasattr(self, "name") and self.name:
            return joins("Character<", self.name, ">", sep="")
        else:
            return "Character<(unnamed)>"

    @property
    def session(self):
        """Return the current session for this character."""
        return self._get_weak("session")

    @session.setter
    def session(self, new_session):
        """Set the current session for this character.

        :param sessions._Session new_session: The session tied to this
                                              character
        :returns None:

        """
        self._set_weak("session", new_session)

    def resume(self):
        """Bring this character into play."""
        self.active = True

    def suspend(self):
        """Remove this character from play."""
        self.active = False


@Character.register_attr("account")
class CharacterAccount(Attribute):

    """The account tied to a character."""

    @classmethod
    def _serialize(cls, value):
        if value is Unset:
            return value
        # Save character accounts by UID
        return value.uid

    @classmethod
    def _deserialize(cls, value):
        if not value:
            return value
        from .accounts import Account
        return Account.find("uid", value, n=1)


@Character.register_attr("name")
class CharacterName(Attribute):

    """A character name."""

    _min_len = 2
    _max_len = 16
    _valid_chars = re.compile(r"^[a-zA-Z]+$")

    # Other modules can add any reservations they need to this list.
    # Reserved character names should be in Titlecase.
    RESERVED = []

    @classmethod
    def _validate(cls, new_value):
        if (not isinstance(new_value, str) or
                not cls._valid_chars.match(new_value)):
            raise ValueError("Character names can only contain letters.")
        name_len = len(new_value)
        if name_len < cls._min_len or name_len > cls._max_len:
            raise ValueError(joins("Character names must be between",
                                   cls._min_len, "and", cls._max_len,
                                   "characters in length."))
        new_value = new_value.title()
        if CharacterName.check_reserved(new_value):
            raise ValueError("That character name is reserved.")
        if Character.find("name", new_value):
            raise ValueError("That character name is already in use.")
        return new_value

    @classmethod
    def check_reserved(cls, name):
        """Check if a character name is reserved.

        :param str name: The character name to check
        :returns bool: True if the name is reserved, else False

        """
        return name in cls.RESERVED


# noinspection PyProtectedMember
@REQUESTS.register
class RequestNewCharacterName(Request):

    """A request for a new character name."""

    initial_prompt = joins("Enter a new character name (character names must"
                           " be between", CharacterName._min_len, "and",
                           CharacterName._max_len, "letters in length): ")
    repeat_prompt = "New character name: "
    confirm = Request.CONFIRM_YES
    confirm_prompt_yn = "'{data}', is that correct? (Y/N) "

    def _validate(self, data):
        try:
            new_name = CharacterName._validate(data)
        except ValueError as exc:
            raise Request.ValidationFailed(*exc.args)
        return new_name


@Character.register_attr("title")
class CharacterTitle(Attribute):

    """A character title."""

    _default = "the newbie"


# noinspection PyUnresolvedReferences
def create_character(session, callback, character=None):
    """Perform a series of requests to create a new character.

    :param sessions._Session session: The session creating a character
    :param callable callback: A callback for when the character is created
    :param Character character: The character in the process of being created
    :returns None:

    """
    if not character:
        character = Character()
        character._savable = False
    if not character.name:
        def _set_name(_session, new_name):
            character.name = new_name
            create_character(_session, callback, character)
        session.request(RequestNewCharacterName, _set_name)
    else:
        character.account = session.account
        character._savable = True
        callback(session, character)


@SHELLS.register
class CharacterShell(Shell):

    """The base shell for characters."""

    state = STATES.playing


@COMMANDS.register
class QuitCommand(Command):

    """A command for quitting the server."""

    def _action(self):
        from .accounts import AccountMenu
        self.session.menu = AccountMenu
        self.session.shell = None


@COMMANDS.register
class ReloadCommand(Command):

    """A command to reload the game server, hopefully without interruption.

    This is similar to the old ROM-style copyover, except that we try and
    preserve a complete game state rather than just the open connections.

    """

    def _action(self):
        from .server import SERVER
        self.session.send("Starting server reload, hold on to your butt.")
        SERVER.reload()


@COMMANDS.register
class SayCommand(Command):

    """A command for saying stuff on the server."""

    no_parse = True

    def _action(self):
        message = self.args[0].strip()
        self.session.send(joins("You say, '", message, "'.", sep=""))


@COMMANDS.register
class TestCommand(Command):

    """A command to test something."""

    def _action(self):
        self.session.send("Great success!")


@COMMANDS.register
class TimeCommand(Command):

    """A command to display the current server time.

    This can be replaced in a game shell to display special in-game time, etc.

    """

    def _action(self):
        from datetime import datetime as dt
        from .timing import TIMERS
        timestamp = dt.fromtimestamp(TIMERS.time).strftime("%c")
        self.session.send("Current time: ", timestamp,
                          " (", TIMERS.get_time_code(), ")", sep="")


CharacterShell.add_verbs(QuitCommand, "quit")
CharacterShell.add_verbs(ReloadCommand, "reload")
CharacterShell.add_verbs(SayCommand, "say", "'")
CharacterShell.add_verbs(TestCommand, "test")
CharacterShell.add_verbs(TimeCommand, "time")
