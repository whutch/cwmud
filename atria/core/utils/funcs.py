# -*- coding: utf-8 -*-
"""Miscellaneous utility functions"""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)


def joins(*parts, sep=" "):
    """Join a sequence as a string with given separator.

    This is a shortcut function that saves you the effort of converting
    each element in a str.join(sequence) call to a str first.

    :param sequence parts: A sequence of items to join
    :param str sep: The separator to join them with
    :return: The newly joined string
    :rtype: str

    """
    if not parts or not any(parts):
        return ""
    return sep.join(map(str, parts))


def type_name(obj):
    """Fetch the type name of an object.

    This is a cosmetic shortcut. I find the normal method very ugly.

    :param any obj: The object you want the type name of
    :return: The type name
    :rtype: str

    """
    return type(obj).__name__


def class_name(obj):
    """Fetch the class name of an object (class or instance).

    Another cosmetic shortcut. The builtin way of getting an instance's class
    name is pretty disgusting (and long), accessing two hidden attributes in
    a row just feels wrong.

    :param any obj: The object you want the class name of
    :return: The class name
    :rtype: str

    """
    if type_name(obj) == "type":
        # It's a class
        return obj.__name__
    else:
        # It's an instance of a class
        return obj.__class__.__name__


def can_be_index(obj):
    """Determine if an object can be used as the index of a sequence.

    :param any obj: The object to test
    :return: Whether it can be an index or not
    :rtype: bool

    """
    try:
        [][obj]
    except TypeError:
        return False
    except IndexError:
        return True


def is_iterable(obj):
    """Determine if an object is iterable.

    :param any obj: The object to test
    :return: Whether it is iterable or not
    :rtype: bool

    """
    try:
        for _ in obj:
            break
    except TypeError:
        return False
    else:
        return True
