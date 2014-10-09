# -*- coding: utf-8 -*-
"""Support decorators."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from weakref import ref


def _make_weak_property(name, validator=None):

    """Return a property object that proxies a weak reference.

    :param str name: The name to store the reference under
    :param function validator: Optional, a function that will be called as a
                               validator before setting the reference, it must
                               accept two arguments, the old object and the
                               new one, and should raise any errors it finds
    :returns property: The constructed property object

    """

    def _getter(self):
        weak_refs = getattr(self, "_weak_refs", None)
        if not weak_refs:
            return None
        weak = weak_refs.get(name)
        return weak() if weak else None

    def _setter(self, new_obj):
        weak_refs = getattr(self, "_weak_refs", None)
        if not weak_refs:
            weak_refs = {}
            setattr(self, "_weak_refs", weak_refs)
        # Call the function as an optional validator
        if validator and callable(validator):
            old_obj = weak_refs.get(name)
            if old_obj:
                old_obj = old_obj()
            validator(self, old_obj, new_obj)
        weak_refs[name] = ref(new_obj) if new_obj else None

    return property(_getter, _setter)


def weak_property(func):
    """Decorate a function to convert it into a proxy for a weak reference.

    The decorated function will act as a post-setter that will be called after
    each time the reference is set.

    :param callable func: The decorated function or other callable
    :returns property: A property object that proxies a weak reference

    """
    return _make_weak_property(func.__name__, func)
