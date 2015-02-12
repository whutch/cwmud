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
from .world import Room
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

    def resume(self, quiet=False):
        """Bring this character into play.

        :param bool quiet: Whether to suppress output from resuming or not
        :returns None:

        """
        if self.room:
            self.room.chars.add(self)
        self.active = True
        if not quiet:
            self.show_room()

    def suspend(self, quiet=False):
        """Remove this character from play.

        :param bool quiet: Whether to suppress output from resuming or not
        :returns None:

        """
        self.active = False
        if self.room and self in self.room.chars:
            self.room.chars.remove(self)

    def act(self, message, context=None, target=None, to=(), and_self=True):
        """Generate and send contextualized Character-based messages.

        This is largely a shortcut and convenience function to avoid a lot of
        individual char.session.send calls with custom-built messages.
        One benefit of keeping the functionality in one place is that we can
        later expand it to cache the generated messages, keyed by template
        string and context.

        :param str message: A specially formatted string that is used to
                            generate the messages.
        :param dict context: The context for the messages.
        :param Character target: A contextual target for the message.
        :param iterable<Character> to: The recipient(s) of the messages
                                       (not including the actor).
        :param bool and_self: Whether to send a message to the actor as well.

        """
        if not context:
            context = {}
        if and_self:
            context["s"] = "you"
            context["ss"] = ""
            if target:
                context["t"] = target.name
                context["ts"] = "s"
            self.session.send(message.format(**context).capitalize())
        if target:
            context["s"] = self.name
            context["ss"] = "s"
            context["t"] = "you"
            context["ts"] = ""
            target.session.send(message.format(**context).capitalize())
        if to:
            context["s"] = self.name
            context["ss"] = "s"
            if target:
                context["t"] = target.name
                context["ts"] = "s"
            msg = message.format(**context).capitalize()
            for char in to:
                if char is not self and char is not target:
                    char.session.send(msg)

    def show_room(self, room=None):
        """Show a room's contents to the session controlling this character.

        :param world.Room room: Optional, the room to show to this character;
                                if None, their current room will be shown
        :returns None:

        """
        if not self.session:
            return
        if not room:
            if not self.room:
                return
            room = self.room
        char_list = "\n".join(["^G{} ^g{}^g is here.^~".format(
                               char.name, char.title)
                               for char in room.chars if char is not self])
        output = joins("^Y", room.name or "An Unnamed Room", "^~\n",
                       "^m", room.description, "^~\n",
                       char_list, "\n" if char_list else "",
                       "^b", "[Exits: nowhere]", "^~", sep="")
        self.session.send(output)


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


@Character.register_attr("room")
class CharacterRoom(Attribute):

    """The room a character is in."""

    @classmethod
    def _validate(cls, new_value):
        if not isinstance(new_value, Room):
            raise ValueError("Character room must be a Room instance.")
        return new_value

    # noinspection PyProtectedMember
    @classmethod
    def _changed(cls, blob, old_value, new_value):
        char = blob._entity
        if char.active:
            # Update the rooms' character sets
            if old_value and char in old_value.chars:
                old_value.chars.remove(char)
            if new_value:
                new_value.chars.add(char)

    @classmethod
    def _serialize(cls, value):
        if value is Unset:
            return value
        # Save character rooms by UID
        return value.uid

    @classmethod
    def _deserialize(cls, value):
        if not value:
            return value
        return Room.load(value)


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
class LogoutCommand(Command):

    """A command for logging out of the game."""

    def _action(self):
        if self.session.character:
            self.session.character.suspend()
        from .accounts import AccountMenu
        self.session.shell = None
        self.session.menu = AccountMenu


@COMMANDS.register
class QuitCommand(Command):

    """A command for quitting the game."""

    def _action(self):
        if self.session.character:
            self.session.character.suspend()
        self.session.close("Okay, goodbye!",
                           log_msg=joins(self.session, "has quit"))


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


@COMMANDS.register
class LookCommand(Command):

    """A command to allow a character to look at things."""

    def _action(self):
        char = self.session.character
        if not char:
            self.session.send("You're not playing a character!")
            return
        if not char.room:
            self.session.send("You're not in a room!")
            return
        char.show_room()


CharacterShell.add_verbs(LogoutCommand, "logout")
CharacterShell.add_verbs(QuitCommand, "quit")
CharacterShell.add_verbs(ReloadCommand, "reload")
CharacterShell.add_verbs(SayCommand, "say", "'")
CharacterShell.add_verbs(TestCommand, "test")
CharacterShell.add_verbs(TimeCommand, "time")
CharacterShell.add_verbs(LookCommand, "look")
