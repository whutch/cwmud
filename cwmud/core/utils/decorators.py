# -*- coding: utf-8 -*-
"""Support decorators."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)


def patch(cls, method_name=None):

    def _inner(func):
        nonlocal method_name
        if not method_name:
            method_name = func.__name__
        setattr(cls, method_name, func)

    return _inner
