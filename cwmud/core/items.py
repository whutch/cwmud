# -*- coding: utf-8 -*-
"""Item management and containers."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from .attributes import Attribute
from .entities import ENTITIES, Entity
from .logs import get_logger
from .pickle import PickleStore
from .storage import STORES
from .utils.funcs import joins


log = get_logger("items")


@ENTITIES.register
class Item(Entity):

    """An item."""

    _store = STORES.register("items", PickleStore("items"))
    _uid_code = "I"

    type = "item"

    def __repr__(self):
        return joins("Item<", self.uid, ">", sep="")


@Item.register_attr("nouns")
class ItemNouns(Attribute):

    """An item's nouns."""

    _default = "item"


@Item.register_attr("name")
class ItemName(Attribute):

    """An item's name."""

    _default = "an item"


@Item.register_attr("short")
class ItemShortDesc(Attribute):

    """An item's short description."""

    _default = "Some sort of item is lying here."


@Item.register_attr("long")
class ItemLongDesc(Attribute):

    """An item's long description."""

    _default = "There's nothing particularly interesting about it."
