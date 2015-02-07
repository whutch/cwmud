# -*- coding: utf-8 -*-
"""Rooms and areas, the virtual space of the MUD."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2015 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

import re

from .entities import ENTITIES, Entity, Attribute
from .logs import get_logger
from .storage import STORES
from .utils.funcs import joins
from .opt.pickle import PickleStore


log = get_logger("world")


@ENTITIES.register
class Room(Entity):

    """A MUD room. Where the magic happens."""

    _store = STORES.register("rooms", PickleStore("rooms"))
    _store_key = "uid"
    _uid_code = "R"

    def __repr__(self):
        name = self.name if self.name else "(unnamed)"
        return joins("Room<", name, ">", sep="")


@Room.register_attr("name")
class RoomName(Attribute):

    """The name of a room."""

    _min_len = 1
    _max_len = 60
    _valid_chars = re.compile(r"^[a-zA-Z ]+$")
    _default = "An Unnamed Room"

    @classmethod
    def _validate(cls, new_value):
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
    def _validate(cls, new_value):
        if not isinstance(new_value, str):
            raise ValueError("Room descriptions must be strings.")
        return new_value
