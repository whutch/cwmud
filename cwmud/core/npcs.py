# -*- coding: utf-8 -*-
"""Non-player characters."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

import re

from .attributes import Attribute
from .characters import Character
from .entities import ENTITIES
from .logs import get_logger
from .utils.funcs import joins


log = get_logger("npcs")


@ENTITIES.register
class NPC(Character):

    """A non-player character."""

    _uid_code = "N"

    type = "npc"

    def __repr__(self):
        return joins("NPC<", self.uid, ">", sep="")

    def get_name(self):
        """Get this character's name."""
        return self.name

    def get_short_description(self):
        """Get this character's short description."""
        return self.short

    def get_long_description(self):
        """Get this character's long description."""
        raise self.long


@NPC.register_attr("name")
class NPCName(Attribute):

    """An NPC's name."""

    _min_len = 2
    _max_len = 24
    _valid_chars = re.compile(r"^[a-zA-Z ]+$")
    default = "an NPC"

    # Other modules can add any reservations they need to this list.
    RESERVED = []

    @classmethod
    def _validate(cls, entity, new_value):
        if (not isinstance(new_value, str) or
                not cls._valid_chars.match(new_value)):
            raise ValueError("NPC names can only contain letters and spaces.")
        name_len = len(new_value)
        if name_len < cls._min_len or name_len > cls._max_len:
            raise ValueError(joins("NPC names must be between",
                                   cls._min_len, "and", cls._max_len,
                                   "characters in length."))
        if NPCName.check_reserved(new_value):
            raise ValueError("That name is reserved.")
        return new_value

    @classmethod
    def check_reserved(cls, name):
        """Check if an NPC name is reserved.

        :param str name: The NPC name to check
        :returns bool: True if the name is reserved, else False

        """
        name = name.lower()
        for reserved in cls.RESERVED:
            if reserved.lower() == name:
                return True
        return False


@NPC.register_attr("short")
class NPCShortDesc(Attribute):

    """An NPC's short description."""

    default = "Some sort of NPC is here."


@NPC.register_attr("long")
class NPCLongDesc(Attribute):

    """An NPC's long description."""

    default = "There's nothing particularly interesting about them."
