# -*- coding: utf-8 -*-
"""Characters, the base of life in the MUD."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2015 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

import re

from .commands import COMMANDS, Command
from .entities import ENTITIES, Entity, Attribute
from .logs import get_logger
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


@Character.register_attr("title")
class CharacterTitle(Attribute):

    """A character title."""

    _default = "the newbie"


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
