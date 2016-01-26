# -*- coding: utf-8 -*-
"""Characters, the base of life in the MUD."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

import re

from .channels import Channel, CHANNELS
from .const import *
from .entities import Attribute, ENTITIES, Entity
from .events import EVENTS
from .logs import get_logger
from .pickle import PickleStore
from .requests import Request, REQUESTS
from .shells import Shell, SHELLS
from .storage import STORES
from .utils.funcs import joins
from .world import get_movement_strings, Room


log = get_logger("characters")


@ENTITIES.register
class Character(Entity):

    """A MUD character.  So full of potential."""

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

        :param sessions.Session new_session: The session tied to this
                                              character
        :returns None:

        """
        self._set_weak("session", new_session)

    def resume(self, quiet=False):
        """Bring this character into play.

        :param bool quiet: Whether to suppress output from resuming or not
        :returns None:

        """
        with EVENTS.fire("char_login", self):
            if self.room:
                self.room.chars.add(self)
            self.active = True
            if not quiet:
                log.info("%s has entered the game.", self)
                CHANNELS["announce"].send(self.name, "has logged in.")
                self.show_room()

    def suspend(self, quiet=False):
        """Remove this character from play.

        :param bool quiet: Whether to suppress output from resuming or not
        :returns None:

        """
        with EVENTS.fire("char_logout", self):
            if not quiet:
                log.info("%s has left the game.", self)
                CHANNELS["announce"].send(self.name, "has logged out.")
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
        :returns None:

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
        is_builder = (self.session.account.trust >= TRUST_BUILDER
                      if self.session.account else False)
        char_list = "\n".join(["^G{} ^g{}^g is here.^~".format(
                               char.name, char.title)
                               for char in room.chars if char is not self])
        extra = " ({})".format(room.get_coord_str()) if is_builder else ""
        self.session.send("^Y", room.name or "A Room", extra, "^~", sep="")
        if room.description:
            self.session.send("^m  ", room.description, "^~", sep="")
        if char_list:
            self.session.send(char_list, "^~", sep="")
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
        :raises TypeError: If `room` is not an instance of Room

        """
        if not isinstance(room, Room):
            raise TypeError("cannot move character to non-room")
        if room is self.room:
            return
        if self.room and depart_msg:
            self.act(depart_msg, depart_context, to=self.room.chars)
        had_chars = bool(room.chars)
        # noinspection PyAttributeOutsideInit
        self.room = room
        if had_chars and arrive_msg:
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
    def _validate(cls, new_value, entity=None):
        from .accounts import Account
        if not isinstance(new_value, Account):
            raise ValueError("Character account must be an Account instance.")
        return new_value

    @classmethod
    def _serialize(cls, value):
        # Save character accounts by UID.
        return value.uid

    @classmethod
    def _deserialize(cls, value):
        from .accounts import Account
        return Account.find("uid", value, n=1)


@Character.register_attr("room")
class CharacterRoom(Attribute):

    """The room a character is in."""

    @classmethod
    def _validate(cls, new_value, entity=None):
        if not isinstance(new_value, Room):
            raise ValueError("Character room must be a Room instance.")
        return new_value

    # noinspection PyProtectedMember
    @classmethod
    def _changed(cls, blob, old_value, new_value):
        char = blob._entity
        if char.active:
            # Update the rooms' character sets.
            if old_value and char in old_value.chars:
                old_value.chars.remove(char)
            if new_value:
                new_value.chars.add(char)

    @classmethod
    def _serialize(cls, value):
        return value.key

    @classmethod
    def _deserialize(cls, value):
        room = Room.load(value, default=None)
        if not room:
            room = Room.load("0,0,0")
        return room


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
    def _validate(cls, new_value, entity=None):
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

    default = "the newbie"


# noinspection PyUnresolvedReferences
def create_character(session, callback, character=None):
    """Perform a series of requests to create a new character.

    :param sessions.Session session: The session creating a character
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
