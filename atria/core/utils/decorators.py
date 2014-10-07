# -*- coding: utf-8 -*-
"""Support decorators."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from weakref import ref


def _make_weak_property(name, post_setter=None):

    """Return a property object that proxies a weak reference.

    :param str name: The name to store the reference under
    :param callable post_setter: Optional, a callable object that will be
                                 called each time the reference is set
    :returns property: The constructed property object

    """

    def _getter(self):
        weak_refs = getattr(self, "_weak_refs", None)
        if not weak_refs:
            return None
        weak = weak_refs.get(name)
        return weak() if weak else None

    def _setter(self, obj):
        weak_refs = getattr(self, "_weak_refs", None)
        if not weak_refs:
            weak_refs = {}
            setattr(self, "_weak_refs", weak_refs)
        weak_refs[name] = ref(obj) if obj else None
        # Call the function as an optional post-setter
        if post_setter and callable(post_setter):
            post_setter(self)

    return property(_getter, _setter)


def weak_property(func):
    """Decorate a function to convert it into a proxy for a weak reference.

    The decorated function will act as a post-setter that will be called after
    each time the reference is set.

    :param callable func: The decorated function or other callable
    :returns property: A property object that proxies a weak reference

    """
    return _make_weak_property(func.__name__, func)
