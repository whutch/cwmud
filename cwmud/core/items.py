# -*- coding: utf-8 -*-
"""Item management and containers."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from collections import Counter

from .attributes import Attribute, ListAttribute, Unset
from .entities import ENTITIES, Entity
from .logs import get_logger
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
        return [item.uid for item in value]

    @classmethod
    def deserialize(cls, entity, value):
        return cls.Proxy(entity, [Item.get(uid) for uid in value])


@ENTITIES.register
class Item(Entity):

    """An item."""

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


@Item.register_attr("container")
class ItemContainer(Attribute):

    """The container an item is in.

    Changing this does not set a reverse relationship, so setting this
    will generally be managed by the container.

    """

    @classmethod
    def serialize(cls, entity, value):
        return value.uid

    @classmethod
    def deserialize(cls, entity, value):
        container = Item.get(value)
        if not container:
            log.warning("Could not load container '%s' for %s",
                        value, entity)
        return container


@ENTITIES.register
class Container(Item):

    """A container item."""

    type = "container"

    def get_weight(self):
        """Get the weight of this container and its contents."""
        return self.weight + self.contents.get_weight()


@Container.register_attr("contents")
class ContainerContents(ItemListAttribute):

    """The contents of a container."""
