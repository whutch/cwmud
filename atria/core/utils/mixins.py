# -*- coding: utf-8 -*-
"""Mix-in support classes."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from .decorators import weak_property


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
            if flag in self._flags:
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


class HasParent:

    """A mix-in to allow objects to link themselves to a parent object.

    Parents are stored with weak references via the weak_properties decorator,
    so a child object will not keep the parent object from being deleted if
    its last strong reference is deleted.

    """

    def __init__(self):
        super().__init__()

    # noinspection PyDocstring,PyUnusedLocal
    @weak_property
    def parent(self, old, new):
        """Validate that this object's lineage doesn't link back to itself."""
        parent = new
        while parent:
            if parent is self:
                raise ValueError("invalid parent due to circular lineage")
            parent = parent.parent

    def get_lineage(self):
        """Return a generator to iterate through this objects lineage.

        Unless an object has the "parent first" flag, it will be yielded first
        in the lineage, before its parent, and so on through the line.

        """
        if hasattr(self, "flags"):
            parent_first = ("parent first" in self.flags)
        else:
            parent_first = False
        parent = self.parent
        if parent and parent_first:
            for obj in parent.get_lineage():
                yield obj
        yield self
        if parent and not parent_first:
            for obj in parent.get_lineage():
                yield obj
