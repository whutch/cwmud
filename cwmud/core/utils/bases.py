# -*- coding: utf-8 -*-
"""Base classes, abstract or otherwise."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from collections import OrderedDict

from .exceptions import AlreadyExists


class Manager:

    """A collection registration manager."""

    _managed_type = None  # The type of object this manager registers.
    _instances = True  # Whether instances or classes are registered.

    def __init__(self):
        """Create a new data store manager."""
        self._items = OrderedDict()

    def __contains__(self, key):
        return key in self._items

    def __getitem__(self, key):
        return self._items[key]

    def register(self, key, item):
        """Register an object with this manager.

        :param hashable key: The key to register the item under
        :param item: The item to be registered
        :returns: The registered item
        :raises AlreadyExists: If an item is already registered with `key`
        :raises TypeError: If `item` is not an instance or subclass of
                           `managed_type`, depending on the value of
                           the `instances` class attribute

        """
        if self._instances:
            if not isinstance(item, self._managed_type):
                raise TypeError("can't register: {} is not an instance of {}"
                                .format(item, self._managed_type))
        else:
            if (not isinstance(item, type) or
                    not issubclass(item, self._managed_type)):
                raise TypeError("can't register: {} is not a subclass of {}"
                                .format(item, self._managed_type))
        if key in self._items:
            raise AlreadyExists(key, self._items[key], item)
        self._items[key] = item
        return item
