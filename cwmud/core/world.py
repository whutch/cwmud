# -*- coding: utf-8 -*-
"""Rooms and areas, the virtual space of the MUD."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

import re

from .attributes import Attribute, Unset
from .entities import ENTITIES, Entity
from .events import EVENTS
from .logs import get_logger
from .utils.funcs import joins


log = get_logger("world")


@ENTITIES.register
class Room(Entity):

    """A MUD room.  Where the magic happens."""

    _uid_code = "R"

    type = "room"

    # These are used to generate Character.act messages.
    _movement_strings = {
        (1, 0, 0): ("east", "the west"),
        (-1, 0, 0): ("west", "the east"),
        (0, 1, 0): ("north", "the south"),
        (0, -1, 0): ("south", "the north"),
        (0, 0, 1): ("up", "below"),
        (0, 0, -1): ("down", "above"),
        (1, 1, 0): ("northeast", "the southwest"),
        (-1, 1, 0): ("northwest", "the southeast"),
        (1, -1, 0): ("southeast", "the northwest"),
        (-1, -1, 0): ("southwest", "the northeast"),
    }

    def __repr__(self):
        name = self.name if self.name else "(unnamed)"
        return joins("Room<", name, ":", self.get_coord_str(), ">", sep="")

    @property
    def coords(self):
        """Return a tuple of this room's x,y,z coordinates."""
        return self.x, self.y, self.z

    def get_coord_str(self):
        """Return a string representing the coordinates for this room.

        :returns str: The coordinate string

        """
        if self.x is Unset or self.y is Unset or self.z is Unset:
            return Unset
        return "{},{},{}".format(self.x, self.y, self.z)

    def set_coord_from_str(self, coord_str):
        """Set this room's coordinates given a string.

        :param str coord_str: A string of coordinates in the form "x,y,z"
        :returns None:

        """
        # noinspection PyAttributeOutsideInit
        self.x, self.y, self.z = map(int, coord_str.split(","))

    @classmethod
    def generate(cls, coord_str, name, description=None):
        """Generate a room.

        :param str coord_str: The string with the room's coordinates
        :param str name: A name for the room
        :param description: Optional, a description for the room
        :returns Room: The generated room

        """
        room = Room()
        room.set_coord_from_str(coord_str)
        room.name = name
        if description is not None:
            room.description = description
        room.save()
        return room

    def get_exits(self):
        """Return the rooms this room connects to.

        :returns dict: The connecting rooms, keyed by direction name

        """
        # This is an inefficient placeholder until an Exit type is in.
        found = {}
        for change, (dir_name, rev_name) in self._movement_strings.items():
            x, y, z = map(sum, zip(self.coords, change))
            room = Room.get(x=x, y=y, z=z)
            if room:
                found[dir_name] = room
        return found

    @classmethod
    def get_movement_strings(cls, change):
        """Return a pair of strings to describe character movement.

        :param tuple<int,int,int> change: A tuple of the (x,y,z) change
        :returns tuple<str,str>: The relevant to and from strings

        """
        return cls._movement_strings.get(change, ("nowhere", "nowhere"))


@Room.register_attr("name")
class RoomName(Attribute):

    """The name of a room."""

    _min_len = 1
    _max_len = 60
    _valid_chars = re.compile(r"^[a-zA-Z ]+$")
    _default = "An Unnamed Room"

    @classmethod
    def validate(cls, entity, new_value):
        if (not isinstance(new_value, str) or
                not cls._valid_chars.match(new_value)):
            raise ValueError("Room names can only contain letters and spaces.")
        name_len = len(new_value)
        if name_len < cls._min_len or name_len > cls._max_len:
            raise ValueError(joins("Room names must be between",
                                   cls._min_len, "and", cls._max_len,
                                   "characters in length."))
        new_value = new_value.title()
        return new_value


@Room.register_attr("description")
class RoomDescription(Attribute):

    """The description of a room."""

    _default = "A nondescript room."

    @classmethod
    def validate(cls, entity, new_value):
        if not isinstance(new_value, str):
            raise ValueError("Room descriptions must be strings.")
        return new_value


class CoordAttribute(Attribute):

    """An attribute for room coordinates."""

    min = None
    max = None

    @classmethod
    def validate(cls, entity, new_value):
        if not isinstance(new_value, int):
            raise ValueError("Coordinates must be integers.")
        if cls.min is not None and new_value < cls.min:
            raise ValueError("Coordinate must be at least {}."
                             .format(cls.min))
        if cls.max is not None and new_value > cls.max:
            raise ValueError("Coordinate cannot be more than {}."
                             .format(cls.max))
        return new_value


@Room.register_attr("x")
class RoomX(CoordAttribute):
    """The X coordinate of a room."""

    @classmethod
    def validate(cls, entity, new_value):
        super().validate(entity, new_value)
        if entity and entity.y is not Unset and entity.z is not Unset:
            if Room.get(x=new_value, y=entity.y, z=entity.z):
                raise ValueError("Room already exists at {},{},{}."
                                 .format(new_value, entity.y, entity.z))
        return new_value


@Room.register_attr("y")
class RoomY(CoordAttribute):
    """The Y coordinate of a room."""

    @classmethod
    def validate(cls, entity, new_value):
        super().validate(entity, new_value)
        if entity and entity.x is not Unset and entity.z is not Unset:
            if Room.get(x=entity.x, y=new_value, z=entity.z):
                raise ValueError("Room already exists at {},{},{}."
                                 .format(entity.x, new_value, entity.z))
        return new_value


@Room.register_attr("z")
class RoomZ(CoordAttribute):
    """The Z coordinate of a room."""

    @classmethod
    def validate(cls, entity, new_value):
        super().validate(entity, new_value)
        if entity and entity.x is not Unset and entity.y is not Unset:
            if Room.get(x=entity.x, y=entity.y, z=new_value):
                raise ValueError("Room already exists at {},{},{}."
                                 .format(entity.x, entity.y, new_value))
        return new_value


@EVENTS.hook("server_boot", "setup_world")
def _hook_server_boot():
    room = Room.get(x=0, y=0, z=0)
    if not room:
        Room.generate("0,0,0", "Starting Room", "There's not much to look at.")
        log.warning("Had to generate initial room at 0,0,0.")
