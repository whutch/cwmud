# -*- coding: utf-8 -*-
"""Characters, the base of life in the MUD."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from . import const
from .attributes import Attribute, SetAttribute
from .entities import ENTITIES, Entity
from .items import ItemListAttribute
from .logs import get_logger
from .shells import Shell, SHELLS
from .utils.funcs import joins
from .world import Room


log = get_logger("characters")


class CharacterSetAttribute(SetAttribute):

    """An attribute for a set of characters."""

    class Proxy(SetAttribute.Proxy):

        def __repr__(self):
            return repr(self._items)

        def add(self, value):
            if not isinstance(value, Character):
                raise TypeError(joins(value, "is not a Character"))
            super().add(value)

    @classmethod
    def serialize(cls, entity, value):
        return [character.uid for character in value]

    @classmethod
    def deserialize(cls, entity, value):
        return cls.Proxy(entity, [Character.get(uid) for uid in value])


@Room.register_attr("chars")
class RoomChars(CharacterSetAttribute):
    """The characters in this room."""


@ENTITIES.register
class Character(Entity):

    """A MUD character.  So full of potential."""

    _uid_code = "C"

    type = "character"

    def __repr__(self):
        return joins("Character<", self.uid, ">", sep="")

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

    def get_name(self):
        """Get this character's name.

        This should be overridden in Character subclasses.

        """
        return "Unnamed"

    def get_short_description(self):
        """Get this character's short description.

        This should be overridden in Character subclasses.

        """
        return "An unnamed character is here."

    def get_long_description(self):
        """Get this character's long description.

        This should be overridden in Character subclasses.

        """
        return "There is nothing particularly interesting about them."

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
                context["t"] = target.get_name()
                context["ts"] = "s"
            self.session.send(_build_msg(message, context))
        if target:
            context["s"] = self.get_name()
            context["ss"] = "s"
            context["t"] = "you"
            context["ts"] = ""
            target.session.send(_build_msg(message, context))
        if to:
            context["s"] = self.get_name()
            context["ss"] = "s"
            if target:
                context["t"] = target.get_name()
                context["ts"] = "s"
            msg = _build_msg(message, context)
            for char in to:
                if char.active and char is not self and char is not target:
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
        is_builder = (self.session.account.trust >= const.TRUST_BUILDER
                      if self.session and self.session.account else False)
        char_list = "\n".join([char.get_short_description()
                               for char in room.chars
                               if char.active and char is not self])
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
        is_builder = (self.session.account.trust >= const.TRUST_BUILDER
                      if self.session and self.session.account else False)
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
        room = Room.get(x=to_x, y=to_y, z=to_z)
        if not room:
            self.session.send("You can't go that way.")
            return
        to_dir, from_dir = Room.get_movement_strings((x, y, z))
        self.move_to_room(room, "{s} move{ss} {dir}.",
                          "{s} arrives from {dir}.",
                          {"dir": to_dir}, {"dir": from_dir})


@Character.register_attr("room")
class CharacterRoom(Attribute):

    """The room a character is in."""

    @classmethod
    def validate(cls, entity, new_value):
        if not isinstance(new_value, Room):
            raise ValueError("Character room must be a Room instance.")
        return new_value

    @classmethod
    def changed(cls, entity, blob, old_value, new_value):
        # Update the rooms' character sets.
        if old_value and entity in old_value.chars:
            old_value.chars.remove(entity)
        if new_value:
            new_value.chars.add(entity)

    @classmethod
    def serialize(cls, entity, value):
        return value.uid

    @classmethod
    def deserialize(cls, entity, value):
        room = Room.get(uid=value)
        if not room:
            room = Room.get(x=0, y=0, z=0, default=KeyError)
        return room


@Character.register_attr("inventory")
class CharacterInventory(ItemListAttribute):

    """A character's inventory."""


@SHELLS.register
class CharacterShell(Shell):

    """The base shell for characters."""

    state = const.STATE_PLAYING
