# -*- coding: utf-8 -*-
"""Text menu system."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from collections import OrderedDict
from weakref import WeakMethod

from .logs import get_logger
from .utils.exceptions import AlreadyExists
from .utils.funcs import class_name, joins
from .utils.mixins import HasWeaks, HasWeaksMeta


log = get_logger("menus")


class MenuManager:

    """A manager for menu registration.

    This is a convenience manager and is not required for the server to
    function.  All of its functionality can be achieved by subclassing,
    instantiating, and referencing menus directly.

    """

    def __init__(self):
        """Create a new menu manager."""
        self._menus = {}

    def __contains__(self, menu):
        return menu in self._menus

    def __getitem__(self, menu):
        return self._menus[menu]

    def register(self, menu):
        """Register a menu.

        This method can be used to decorate a Menu class.

        :param Menu menu: The menu to be registered
        :returns Menu: The registered menu
        :raises AlreadyExists: If a menu with that class name already exists
        :raises TypeError: If the supplied or decorated class is not a
                           subclass of Menu

        """
        if (not isinstance(menu, type) or
                not issubclass(menu, Menu)):
            raise TypeError("must be subclass of Menu to register")
        name = menu.__name__
        if name in self._menus:
            raise AlreadyExists(name, self._menus[name], menu)
        self._menus[name] = menu
        return menu


# noinspection PyDocstring
class _MenuMeta(HasWeaksMeta):

    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        cls._entries = OrderedDict()

    def add_entry(cls, key, description, callback=None):
        """Add an entry to this menu.

        If you do not provide `callback`, this will instead return a
        decorator that will use the decorated callable as the callback.

        :param str key: A single-character key the entry will be accessed by
        :param str description: A description line for the entry
        :param callable callback: A callback for when the entry is chosen
        :returns None:
        :raises AlreadyExists: If an entry with that key already exists
        :raises ValueError: If `key` is not a single character string

        """
        def _inner(_callback):
            nonlocal key, description
            if not key or not isinstance(key, str) or len(key) > 1:
                raise ValueError(joins("menu entry keys must be a single"
                                       "character:", key))
            if key in " \t\n\r\f\v":
                raise ValueError("menu entry keys cannot be whitespace")
            key = key.upper()
            entry = (description, _callback)
            if key in cls._entries:
                raise AlreadyExists(key, cls._entries[key], entry)
            cls._entries[key] = entry
            return _callback
        if callback is not None:
            return _inner(callback)
        else:
            return _inner

    def remove_entry(cls, key):
        """Remove an entry from this menu.

        :param str key: The key of the entry to remove
        :returns None:
        :raises KeyError: If an entry with that key is not found

        """
        key = key.upper()
        if key not in cls._entries:
            raise KeyError(joins("entry not found in ", class_name(cls),
                                 ": ", key, sep=""))
        del cls._entries[key]


class Menu(HasWeaks, metaclass=_MenuMeta):

    """A text menu."""

    # Constants, don't change these.
    ORDER_BY_ADDED = 1
    ORDER_BY_ALPHA = 2

    # Defaults, override these on subclasses.
    title = "MENU:"
    prompt = ": "
    error = "Bad menu key: {key}"
    ordering = ORDER_BY_ALPHA
    title_color = "^Y"
    key_color = "^W"
    spacer_color = "^Y"
    description_color = "^w"
    prompt_color = "^Y"
    error_color = "^R"

    def __init__(self, session):

        """Create an instance of this menu tied to a session."""

        super().__init__()
        self.session = session
        self._entries = self._entries.copy()
        self._entry_order = []

        # TODO: Find out why these next two prevent these from being
        # garbage collected.  I know that bound methods create circular
        # references with the instances but Python should detect that and
        # free both objects.  It's not.

        # self.add_entry = self._inst_add_entry
        # self.remove_entry = self._inst_remove_entry

        # For now this is a work-around:
        self._add_entry_wr = WeakMethod(self._inst_add_entry)
        self._remove_entry_wr = WeakMethod(self._inst_remove_entry)

        def _add_entry(key, description, callback=None):
            return self._add_entry_wr()(key, description, callback)

        def _remove_entry(key):
            self._remove_entry_wr()(key)

        self.add_entry = _add_entry
        self.remove_entry = _remove_entry

        # Perform any instance-specific finalization.
        self._init()
        self._update_order()

    @property
    def session(self):
        """Return the current session for this menu."""
        return self._get_weak("session")

    @session.setter
    def session(self, new_session):
        """Set the current session for this menu.

        :param Session new_session: The session tied to this menu
        :returns None:

        """
        self._set_weak("session", new_session)

    # noinspection PyMethodMayBeStatic
    def _init(self):
        """Prepare this menu after instantiation.

        Override this to perform any necessary localization or additional
        entry management specific to the session.

        """

    def _inst_add_entry(self, key, description, callback=None):
        """Add an entry to this menu.

        If you do not provide `callback`, this will instead return a
        decorator that will use the decorated callable as the callback.

        :param str key: A single-character key the entry will be accessed by
        :param str description: A description line for the entry
        :param callable callback: A callback for when the entry is chosen
        :returns None:
        :raises AlreadyExists: If an entry with that key already exists
        :raises ValueError: If `key` is not a single character string

        """
        def _inner(_callback):
            nonlocal key, description
            if not key or not isinstance(key, str) or len(key) > 1:
                raise ValueError(joins("menu entry keys must be a single"
                                       "character:", key))
            if key in " \t\n\r\f\v":
                raise ValueError("menu entry keys cannot be whitespace")
            key = key.upper()
            entry = (description, _callback)
            if key in self._entries:
                raise AlreadyExists(key, self._entries[key], entry)
            self._entries[key] = entry
            self._update_order()
            return _callback
        if callback is not None:
            return _inner(callback)
        else:
            return _inner

    def _inst_remove_entry(self, key):
        """Remove an entry from this menu.

        :param str key: The key of the entry to remove
        :returns None:
        :raises KeyError: If an entry with that key is not found

        """
        key = key.upper()
        if key not in self._entries:
            raise KeyError(joins("entry not found in ", class_name(self),
                                 ": ", key, sep=""))
        del self._entries[key]
        self._update_order()

    def _update_order(self):
        """Update the menu entry order cache."""
        keys = self._entries.keys()
        if self.ordering == self.ORDER_BY_ADDED:
            self._entry_order = keys
        elif self.ordering == self.ORDER_BY_ALPHA:
            self._entry_order = list(sorted(keys))

    def display(self):
        """Send this menu to the session."""
        self.session.send("")  # Send a newline.
        if self.title is not None:
            self.session.send(self.title_color, self.title, "^~", sep="")
        for key in self._entry_order:
            description = self._entries[key][0]
            self.session.send(self.key_color, key, self.spacer_color, ") ",
                              self.description_color, description,
                              "^~", sep="")

    def get_prompt(self):
        """Generate the current prompt for this menu."""
        return joins(self.prompt_color, self.prompt, "^~", sep="")

    def parse(self, data):
        """Parse input from the client session.

        Only the first character of any input sent will be used.

        :param str data: The data to be parsed
        :returns None:

        """
        data = data[0].upper()
        if data not in self._entries:
            self.session.send(self.error_color, self.error.format(key=data),
                              "^~", sep="")
            self.display()
        else:
            callback = self._entries[data][1]
            callback(self.session)


# We create a global MenuManager here for convenience, and while the
# server will generally only need one to work with, they are NOT singletons
# and you can make more MenuManager instances if you like.
MENUS = MenuManager()
