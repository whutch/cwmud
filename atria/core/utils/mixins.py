# -*- coding: utf-8 -*-
"""Mix-in support classes."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)


class _FlagSet:

    """A set of flags on an object. Used by the HasFlags mix-in.

    A flag can be any hashable object (anything you can put in a set).

    """

    def __init__(self):
        self._flags = set()

    def __contains__(self, flag):
        return flag in self._flags

    def __iter__(self):
        return iter(self._flags)

    def __bool__(self):
        return bool(self._flags)

    @property
    def as_tuple(self):
        """Return the current set of flags as a tuple."""
        return tuple(self._flags)

    def has(self, *flags):
        """Return whether this set contains all of the given flags.

        :param hashable flags: The flags to check for
        :returns bool: Whether this flag set contains all given flags

        """
        return all((True if flag in self._flags else False for flag in flags))

    def has_any(self, *flags):
        """Return whether this set contains one or more of the given flags.

        :param hashable flags: The flags to check for
        :returns bool: Whether this flag set contains some of the given flags

        """
        return any((True if flag in self._flags else False for flag in flags))

    def add(self, *flags):
        """Add one or more flags to this set.

        :param hashable flags: The flags to add
        :returns: None

        """
        for flag in flags:
            self._flags.add(flag)

    def drop(self, *flags):
        """Drop one or more flags from this set.

        :param hashable flags: The flags to drop
        :returns: None

        """
        for flag in flags:
            self._flags.remove(flag)

    def toggle(self, *flags):
        """Toggle whether one or more flags are in this set.

        :param hashable flags: The flags to toggle
        :returns: None

        """
        for flag in flags:
            if flag in self._flags:
                self._flags.remove(flag)
            else:
                self._flags.add(flag)


class HasFlags:

    """A mix-in to allow 'flagging' an object through a series of methods."""

    def __init__(self):
        super().__init__()
        self._flag_set = _FlagSet()

    @property
    def flags(self):
        """Return this object's flag set."""
        return self._flag_set
