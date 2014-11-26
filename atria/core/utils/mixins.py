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


class HasFlagsMeta(type):

    """A metaclass to support flagging of classes themselves."""

    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        cls._flag_set = _FlagSet()

    # noinspection PyDocstring
    @property
    def flags(cls):
        """Return this class's flag set."""
        return cls._flag_set


class HasFlags(metaclass=HasFlagsMeta):

    """A mix-in to allow 'flagging' an object through a series of methods.

    Each individual class or instance of a class that subclasses this will
    have a separate flag set, there is no inheritance.

    """

    def __init__(self):
        super().__init__()
        self._flag_set = _FlagSet()

    @property
    def flags(self):
        """Return this instance's flag set."""
        return self._flag_set


class HasWeaksMeta(type):

    """A metaclass to support storing weak references on classes themselves."""

    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        cls._weak_refs = {}

    def _get_weak(cls, name):
        weak = cls._weak_refs.get(name)
        return weak() if weak else None

    def _set_weak(cls, name, obj):
        if obj is None:
            cls._del_weak(name)
        else:
            cls._weak_refs[name] = ref(obj)

    def _del_weak(cls, name):
        if name in cls._weak_refs:
            del cls._weak_refs[name]


class HasWeaks(metaclass=HasWeaksMeta):

    """A mix-in to allow objects to store weak references to other objects.

    Each individual class or instance of a class that subclasses this will
    have a separate weak reference dict, there is no inheritance.

    """

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


# noinspection PyDocstring
class HasParentMeta(type):

    """A metaclass to support arbitrary class lineages through `parent`."""

    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        cls._parent = None
        cls._parent_first = False

    @property
    def parent(cls):
        """Get the parent of this class."""
        # noinspection PyCallingNonCallable
        return cls._parent

    @parent.setter
    def parent(cls, obj):
        """Set the parent of this class.

        :param HasParent obj: The new parent; must subclass HasParent
        :returns: None
        :raises TypeError: If ``obj`` cannot be a parent
        :raises ValueError: If this parent results in a circular lineage

        """
        if obj is None:
            cls._parent = None
        else:
            # Check that this object can be a parent
            if not hasattr(obj, "parent"):
                raise TypeError("given object cannot be a parent")
            # Check for a circular lineage through this parent
            check_obj = obj
            while check_obj:
                if check_obj is cls:
                    raise ValueError("invalid parent due to circular lineage")
                check_obj = check_obj.parent
            # Lineage is good
            cls._parent = obj

    def get_lineage(cls, priority=0):
        """Return a generator to iterate through this object's lineage.

        Unless an object has _parent_first set True, it will be yielded first
        in the lineage, before its parent, and so on through the line.

        :param int priority: If zero, this will iterate over the full lineage;
                             if positive, this will only iterate over objects
                             that have priority over this object; if negative,
                             this will only iterate over objects that this
                             object has priority over
        :returns generator: An iterator through this object's lineage

        """
        parent = cls.parent  # Save a bunch of weakref de-referencing.
        if parent and cls._parent_first and priority >= 0:
            for obj in parent.get_lineage():
                yield obj
        if priority == 0:
            yield cls
        if parent and not cls._parent_first and priority <= 0:
            for obj in parent.get_lineage():
                yield obj

    def get_ancestors(cls):
        """Return a generator to iterate through this object's ancestors.

        :returns generator: An iterator through this object's ancestry

        """
        if cls.parent:
            yield cls.parent
            for obj in cls.parent.get_ancestors():
                yield obj

    def has_ancestor(cls, obj):
        """Return whether this object has another object as an ancestor.

        :param HasParent obj: The object to search for
        :returns bool: Whether the object was found in this object's ancestry

        """
        return obj in cls.get_ancestors()


class HasParent(metaclass=HasParentMeta):

    """A mix-in to allow classes to link themselves to a parent class.

    For now, the parent system is only for the class objects themselves and
    not their instances, unless we can think of a solid use-case otherwise.

    """

    def __init__(self):
        super().__init__()
