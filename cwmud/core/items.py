# -*- coding: utf-8 -*-
"""Item management and containers."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from collections import Counter

from .attributes import Attribute, ListAttribute, Unset
from .entities import ENTITIES, Entity
from .logs import get_logger
from .pickle import PickleStore
from .storage import STORES
from .utils.funcs import joins


log = get_logger("items")


class ItemListAttribute(ListAttribute):

    """An attribute for a list of items."""

    class Proxy(ListAttribute.Proxy):

        def __repr__(self):
            return repr(self._items)

        def __setitem__(self, index, value):
            if not isinstance(value, Item):
                raise TypeError(joins(value, "is not an Item"))
            value.container = self._entity
            super().__setitem__(index, value)

        def __delitem__(self, index):
            self._items[index].container = Unset
            super().__delitem__(index)

        def insert(self, index, value):
            if not isinstance(value, Item):
                raise TypeError(joins(value, "is not an Item"))
            value.container = self._entity
            super().insert(index, value)

        def get_counts(self):
            return Counter([item.name for item in self._items]).items()

        def get_weight(self):
            return sum([item.get_weight() for item in self._items])

    @classmethod
    def serialize(cls, entity, value):
        return [item.key for item in value]

    @classmethod
    def deserialize(cls, entity, value):
        return cls.Proxy(entity, [Item.load(key) for key in value])


@ENTITIES.register
class Item(Entity):

    """An item."""

    _store = STORES.register("items", PickleStore("items"))
    _uid_code = "I"

    type = "item"

    def __repr__(self):
        return joins("Item<", self.uid, ">", sep="")

    def get_weight(self):
        """Get the weight of this item."""
        return self.weight


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


@Item.register_attr("weight")
class ItemWeight(Attribute):

    """An item's weight."""

    _default = 0
