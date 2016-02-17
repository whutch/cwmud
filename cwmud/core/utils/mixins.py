# -*- coding: utf-8 -*-
"""Mix-in support classes."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from collections.abc import MutableMapping
from weakref import ref, WeakMethod, WeakValueDictionary


"""
A note on using multiple mix-ins with metaclasses:

If you subclass multiple mix-in classes that each have independent metaclasses,
you will need to first create a new metaclass that subclasses the metaclasses
of each of the mix-ins you are using and then use that as the metaclass for
your new class. For example:

class _MyClassMeta(HasFlagsMeta, HasWeaksMeta):
    pass

class MyClass(HasFlags, HasWeaks, metaclass=_MyClassMeta):
    ...

"""


# noinspection PyProtectedMember
class _FlagSet:

    """A set of flags on an object.  Used by the HasFlags mix-in.

    A flag can be any hashable object (anything you can put in a set).

    """

    def __init__(self, owner=None):
        self._flags = set()
        self._owner_ref = ref(owner) if owner else None

    @property
    def _owner(self):
        return self._owner_ref() if self._owner_ref else None

    def __contains__(self, flag):
        return flag in self._flags

    def __iter__(self):
        return iter(self._flags)

    def __bool__(self):
        return bool(self._flags)

    def __repr__(self):
        return "Flags<{}>".format(", ".join(sorted(self._flags)))

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
        :returns None:

        """
        for flag in flags:
            self._flags.add(flag)
        if self._owner:
            self._owner._flags_changed()

    def drop(self, *flags):
        """Drop one or more flags from this set.

        :param hashable flags: The flags to drop
        :returns None:

        """
        for flag in flags:
            if flag in self._flags:
                self._flags.remove(flag)
        if self._owner:
            self._owner._flags_changed()

    def toggle(self, *flags):
        """Toggle whether one or more flags are in this set.

        :param hashable flags: The flags to toggle
        :returns None:

        """
        for flag in flags:
            if flag in self._flags:
                self._flags.remove(flag)
            else:
                self._flags.add(flag)
        if self._owner:
            self._owner._flags_changed()


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
        self._flag_set = _FlagSet(self)

    @property
    def flags(self):
        """Return this instance's flag set."""
        return self._flag_set

    # noinspection PyMethodMayBeStatic
    def _flags_changed(self):
        """Perform any callbacks for when the flag set has changed.

        Override this to perform any necessary post-change actions.

        """


# noinspection PyProtectedMember
class _Tags(MutableMapping):

    """A mapping of tags on an object.  Used by the HasTags mix-in.

    Tags are used to store arbitrary data on another object.  Tag keys and
    values are functionally equivalent to dictionary keys and values.

    """

    def __init__(self, owner=None):
        self._tags = {}
        self._owner_ref = ref(owner) if owner else None

    @property
    def _owner(self):
        return self._owner_ref() if self._owner_ref else None

    def __repr__(self):
        items = ["{}: {}".format(k, v) for k, v in self._tags.items()]
        return "Tags{{{}}}".format(", ".join(sorted(items)))

    def __bool__(self):
        return bool(self._tags)

    def __contains__(self, key):
        return key in self._tags

    def __iter__(self):
        return iter(self._tags)

    def __len__(self):
        return len(self._tags)

    def __getitem__(self, key):
        return self._tags[key]

    def __setitem__(self, key, value):
        self._tags[key] = value
        if self._owner:
            self._owner._tags_changed()

    def __delitem__(self, key):
        del self._tags[key]
        if self._owner:
            self._owner._tags_changed()

    @property
    def as_dict(self):
        """Return a copy of the current tags as a dict."""
        return self._tags.copy()


class HasTags:

    """A mix-in to allow 'tagging' an object to store arbitrary data."""

    def __init__(self):
        super().__init__()
        self._tags = _Tags(self)

    @property
    def tags(self):
        """Return this instance's tag collection."""
        return self._tags

    # noinspection PyMethodMayBeStatic
    def _tags_changed(self):
        """Perform any callbacks for when the tag collection has changed.

        Override this to perform any necessary post-change actions.

        """


class HasWeaksMeta(type):

    """A metaclass to support storing weak references on classes themselves."""

    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        cls._weak_refs = WeakValueDictionary()

    def _get_weak(cls, name):
        return cls._weak_refs.get(name)

    def _set_weak(cls, name, obj):
        if obj is None:
            cls._del_weak(name)
        else:
            cls._weak_refs[name] = obj

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
        self._get_weak_wr = WeakMethod(self._inst_get_weak)
        self._get_weak = lambda k: self._get_weak_wr()(k)
        self._set_weak_wr = WeakMethod(self._inst_set_weak)
        self._set_weak = lambda k, o: self._set_weak_wr()(k, o)
        self._del_weak_wr = WeakMethod(self._inst_del_weak)
        self._del_weak = lambda k: self._del_weak_wr()(k)
        self._weak_refs = WeakValueDictionary()

    def _inst_get_weak(self, name):
        return self._weak_refs.get(name)

    def _inst_set_weak(self, name, obj):
        if obj is None:
            self._del_weak(name)
        else:
            self._weak_refs[name] = obj

    def _inst_del_weak(self, name):
        if name in self._weak_refs:
            del self._weak_refs[name]


# noinspection PyDocstring
class HasParentMeta(type):

    """A metaclass to support arbitrary class lineages through `parent`."""

    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        cls.parent_first = False

    def get_lineage(cls, priority=0, yielded=None):
        """Return a generator to iterate through this object's lineage.

        Unless an object has parent_first set True, it will be yielded first
        in the lineage, before its parent, and so on through the line.

        :param int priority: If zero, this will iterate over the full lineage;
                             if positive, this will only iterate over objects
                             that have priority over this object; if negative,
                             this will only iterate over objects that this
                             object has priority over
        :param set yielded: A set used internally for keeping track of which
                            parents have already been yielded
        :returns generator: An iterator through this object's lineage

        """
        if yielded is None:
            yielded = set()
        if cls.parent_first and priority >= 0:
            for base in cls.__bases__:
                if issubclass(base, HasParent):
                    for obj in base.get_lineage(yielded=yielded):
                        yield obj
        if priority == 0 and cls not in yielded and cls is not HasParent:
            yielded.add(cls)
            yield cls
        if not cls.parent_first and priority <= 0:
            for base in cls.__bases__:
                if issubclass(base, HasParent):
                    for obj in base.get_lineage(yielded=yielded):
                        yield obj

    def get_ancestors(cls, yielded=None):
        """Return a generator to iterate through this object's ancestors.

        :returns generator: An iterator through this object's ancestry

        """
        if yielded is None:
            yielded = set()
        for base in cls.__bases__:
            if issubclass(base, HasParent) and base is not HasParent:
                if base not in yielded:
                    yielded.add(base)
                    yield base
                for obj in base.get_ancestors(yielded):
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
