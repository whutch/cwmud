# -*- coding: utf-8 -*-
"""Characters, the base of life in the MUD."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2015 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

import re

from .commands import COMMANDS, Command
from .const import *
from .entities import ENTITIES, Entity, Attribute
from .logs import get_logger
from .pickle import PickleStore
from .requests import REQUESTS, Request
from .shells import SHELLS, Shell
from .storage import STORES
from .world import Room, get_movement_strings
from .utils.funcs import joins


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
        def _build_msg(template, _context):
            return ".".join([part[:1].upper() + part[1:] for part in
                             template.format(**_context).split(".")])
        if not context:
            context = {}
        if and_self:
            context["s"] = "you"
            context["ss"] = ""
            if target:
                context["t"] = target.name
                context["ts"] = "s"
            self.session.send(_build_msg(message, context))
        if target:
            context["s"] = self.name
            context["ss"] = "s"
            context["t"] = "you"
            context["ts"] = ""
            target.session.send(_build_msg(message, context))
        if to:
            context["s"] = self.name
            context["ss"] = "s"
            if target:
                context["t"] = target.name
                context["ts"] = "s"
            msg = _build_msg(message, context)
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
        is_builder = self.session.account.trust >= TRUST_BUILDER
        char_list = "\n".join(["^G{} ^g{}^g is here.^~".format(
                               char.name, char.title)
                               for char in room.chars if char is not self])
        extra = " ({})".format(room.get_coord_str()) if is_builder else ""
        self.session.send("^Y", room.name or "An Unnamed Room", extra, "^~\n",
                          "^m  ", room.description, "^~\n",
                          char_list, "\n" if char_list else "", "^~",
                          sep="", end="")
        self.show_exits()

    def show_exits(self, room=None, short=False):
        """Show a room's exits to the session controlling this character.

        :param world.Room room: Optional, the room to show the exits for;
                                if None, their current room's exits are shown
        :param bool short: Whether to show the exits in short form or long
        :returns None:

        """
        if not self.session:
            return
        if not room:
            if not self.room:
                return
            room = self.room
        is_builder = self.session.account.trust >= TRUST_BUILDER
        exits = room.get_exits()
        if short:
            exits_string = "^b[Exits: {}]^~".format(
                " ".join(sorted(exits.keys())) if exits else "none")
        else:
            exits_string = "^bExits:\n{}^~".format(
                "\n".join(["  {} - {}{}".format(dir_name, _room.name,
                                                " ({})".format(
                                                    _room.get_coord_str())
                                                if is_builder else "")
                           for dir_name, _room in sorted(exits.items())])
                if exits else "  none")
        self.session.send(exits_string)

    def move_to_room(self, room, depart_msg="", arrive_msg="",
                     depart_context=None, arrive_context=None):
        """Move this character to a room.

        :param world.Room room: The room to move this character to
        :param str depart_msg: Optional, an act message for departure
        :param str arrive_msg: Optional, an act message for arrival
        :param dict depart_context: Optional, a context for the departure
        :param dict arrive_context: Optional, a context for the arrival
        :returns None:

        """
        if not room:
            return
        if depart_msg:
            self.act(depart_msg, depart_context, to=self.room.chars)
        # noinspection PyAttributeOutsideInit
        self.room = room
        if arrive_msg:
            self.act(arrive_msg, arrive_context,
                     to=self.room.chars, and_self=False)
        self.show_room()

    def move_direction(self, x=0, y=0, z=0):
        """Move this character to the room in a given direction.

        :param int x: The change in the X coordinate
        :param int y: The change in the Y coordinate
        :param int z: The change in the Z coordinate
        :returns None:

        """
        if not x and not y and not z:
            # They apparently don't want to go anywhere..
            return
        if not self.room:
            # Can't move somewhere from nowhere.
            return
        to_x, to_y, to_z = map(sum, zip(self.room.coords, (x, y, z)))
        room = Room.find("x", to_x, "y", to_y, "z", to_z, n=1)
        if not room:
            self.session.send("You can't go that way.")
            return
        to_dir, from_dir = get_movement_strings((x, y, z))
        self.move_to_room(room, "{s} move{ss} {dir}.",
                          "{s} arrives from {dir}.",
                          {"dir": to_dir}, {"dir": from_dir})


@Character.register_attr("account")
class CharacterAccount(Attribute):

    """The account tied to a character."""

    @classmethod
    def _validate(cls, new_value):
        from .accounts import Account
        if not isinstance(new_value, Account):
            raise ValueError("Character account must be an Account instance.")
        return new_value

    @classmethod
    def _serialize(cls, value):
        # Save character accounts by UID
        return value.uid

    @classmethod
    def _deserialize(cls, value):
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
        # Save character rooms by UID
        return value.uid

    @classmethod
    def _deserialize(cls, value):
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

    state = STATE_PLAYING


@COMMANDS.register
class LogoutCommand(Command):

    """A command for logging out of the game."""

    def _action(self):
        if self.session.char:
            self.session.char.suspend()
        from .accounts import AccountMenu
        self.session.shell = None
        self.session.menu = AccountMenu


@COMMANDS.register
class QuitCommand(Command):

    """A command for quitting the game."""

    def _action(self):
        if self.session.char:
            self.session.char.suspend()
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

    """A command for room-specific communication."""

    no_parse = True

    def _action(self):
        char = self.session.char
        message = self.args[0].strip()
        char.act("{s} say{ss}, '{msg}'.", {"msg": message},
                 to=char.room.chars)


@COMMANDS.register
class GossipCommand(Command):

    """A command for global communication."""

    no_parse = True

    def _action(self):
        char = self.session.char
        message = self.args[0].strip()
        char.act("^M{s} gossip{ss}, '{msg}'.^~", {"msg": message},
                 to=Character.all())


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
        char = self.session.char
        if not char:
            self.session.send("You're not playing a character!")
            return
        if not char.room:
            self.session.send("You're not in a room!")
            return
        char.show_room()


@COMMANDS.register
class NorthCommand(Command):

    """A command to allow a character to move north."""

    def _action(self):
        char = self.session.char
        if not char:
            self.session.send("You're not playing a character!")
            return
        if not char.room:
            self.session.send("You're not in a room!")
            return
        char.move_direction(y=1)


@COMMANDS.register
class SouthCommand(Command):

    """A command to allow a character to move south."""

    def _action(self):
        char = self.session.char
        if not char:
            self.session.send("You're not playing a character!")
            return
        if not char.room:
            self.session.send("You're not in a room!")
            return
        char.move_direction(y=-1)


@COMMANDS.register
class WestCommand(Command):

    """A command to allow a character to move west."""

    def _action(self):
        char = self.session.char
        if not char:
            self.session.send("You're not playing a character!")
            return
        if not char.room:
            self.session.send("You're not in a room!")
            return
        char.move_direction(x=-1)


@COMMANDS.register
class EastCommand(Command):

    """A command to allow a character to move east."""

    def _action(self):
        char = self.session.char
        if not char:
            self.session.send("You're not playing a character!")
            return
        if not char.room:
            self.session.send("You're not in a room!")
            return
        char.move_direction(x=1)


@COMMANDS.register
class UpCommand(Command):

    """A command to allow a character to move up."""

    def _action(self):
        char = self.session.char
        if not char:
            self.session.send("You're not playing a character!")
            return
        if not char.room:
            self.session.send("You're not in a room!")
            return
        char.move_direction(z=1)


@COMMANDS.register
class DownCommand(Command):

    """A command to allow a character to move down."""

    def _action(self):
        char = self.session.char
        if not char:
            self.session.send("You're not playing a character!")
            return
        if not char.room:
            self.session.send("You're not in a room!")
            return
        char.move_direction(z=-1)


@COMMANDS.register
class ExitsCommand(Command):

    """A command to display the exits of the room a character is in."""

    def _action(self):
        char = self.session.char
        if not char:
            self.session.send("You're not playing a character!")
        if not char.room:
            self.session.send("You're not in a room!")
            return
        char.show_exits(short=True if self.args and
                        self.args[0] == "short" else False)


@COMMANDS.register
class DigCommand(Command):

    """A command for creating new rooms."""

    _dirs = {
        "east": (1, 0, 0),
        "west": (-1, 0, 0),
        "north": (0, 1, 0),
        "south": (0, -1, 0),
        "up": (0, 0, 1),
        "down": (0, 0, -1),
    }

    def _action(self):
        char = self.session.char
        if not char.room:
            self.session.send("You're not in a room!")
            return
        for dir_name, change in self._dirs.items():
            if dir_name.startswith(self.args[0]):
                break
        else:
            self.session.send("That's not a direction.")
            return
        x, y, z = map(sum, zip(char.room.coords, change))
        room = Room.find("x", x, "y", y, "z", z, n=1)
        if room:
            self.session.send("There's already a room over there!")
            return
        room = Room()
        room.x, room.y, room.z = x, y, z
        room.save()
        char.move_to_room(room, "{s} tunnel{ss} out a new room to the {dir}!",
                          depart_context={"dir": dir_name})


@COMMANDS.register
class NameCommand(Command):

    """A command for naming things."""

    no_parse = True

    def _action(self):
        # This will later be a general OLC command for naming anything but
        # for now you can just name rooms.
        char = self.session.char
        if not char.room:
            self.session.send("You're not in a room!")
            return
        char.room.name = self.args[0].strip().title()
        self.session.send("Ok.")


@COMMANDS.register
class CommitCommand(Command):

    """A command to force a global store commit."""

    def _action(self):
        from .entities import ENTITIES
        from .storage import STORES
        ENTITIES.save()
        STORES.commit()
        self.session.send("Ok.")


# Movement commands
CharacterShell.add_verbs(NorthCommand, "north", "n")
CharacterShell.add_verbs(SouthCommand, "south", "s")
CharacterShell.add_verbs(WestCommand, "west", "w")
CharacterShell.add_verbs(EastCommand, "east", "e")
CharacterShell.add_verbs(UpCommand, "up", "u")
CharacterShell.add_verbs(DownCommand, "down", "d")
CharacterShell.add_verbs(ExitsCommand, "exits", "ex")

# Information commands
CharacterShell.add_verbs(LookCommand, "look", "l")
CharacterShell.add_verbs(TimeCommand, "time")

# Communication commands
CharacterShell.add_verbs(SayCommand, "say", "'")
CharacterShell.add_verbs(GossipCommand, "gossip", "\"")

# Connection commands
CharacterShell.add_verbs(QuitCommand, "quit")
CharacterShell.add_verbs(LogoutCommand, "logout")

# Admin commands
CharacterShell.add_verbs(ReloadCommand, "reload")
CharacterShell.add_verbs(TestCommand, "test")
CharacterShell.add_verbs(CommitCommand, "commit")

# OLC commands
CharacterShell.add_verbs(DigCommand, "dig")
CharacterShell.add_verbs(NameCommand, "name")
