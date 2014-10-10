# -*- coding: utf-8 -*-
"""Mix-in support classes."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from weakref import ref


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


class HasWeaks:

    """A mix-in to allow objects to store weak references to other objects."""

    def __init__(self):
        super().__init__()
        self._weak_refs = {}

    def _get_weak(self, name):
        weak = self._weak_refs.get(name)
        return weak() if weak else None

    def _set_weak(self, name, obj):
        if obj is None:
            self._del_weak(name)
        else:
            self._weak_refs[name] = ref(obj)

    def _del_weak(self, name):
        if name in self._weak_refs:
            del self._weak_refs[name]


class HasParent(HasWeaks):

    """A mix-in to allow objects to link themselves to a parent object.

    Parents are stored with weak references via the HasWeaks mix-in, so a
    child object will not keep the parent object from being deleted if its
    last strong reference is deleted.

    """

    def __init__(self):
        super().__init__()

    @property
    def parent(self):
        """Get the parent of this object."""
        return self._get_weak("parent")

    @parent.setter
    def parent(self, obj):
        """Set the parent of this object.

        :param HasParent obj: The new parent; must subclass HasParent
        :returns: None
        :raises TypeError: If ``obj`` cannot be a parent
        :raises ValueError: If this parent results in a circular lineage

        """
        if obj is not None:
            # Check that this object can be a parent
            if not hasattr(obj, "parent"):
                raise TypeError("given object cannot be a parent")
            # Check for a circular lineage through this parent
            check_obj = obj
            while check_obj:
                if check_obj is self:
                    raise ValueError("invalid parent due to circular lineage")
                check_obj = check_obj.parent
        # Lineage is good
        self._set_weak("parent", obj)

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
