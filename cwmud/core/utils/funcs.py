# -*- coding: utf-8 -*-
"""Miscellaneous utility functions."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

import bcrypt


def joins(*parts, sep=" "):
    """Join a sequence as a string with given separator.

    This is a shortcut function that saves you the effort of converting
    each element in a str.join(sequence) call to a str first.

    :param sequence parts: A sequence of items to join
    :param str sep: The separator to join them with
    :returns str: The newly joined string

    """
    if not parts or not any(parts):
        return ""
    return sep.join(map(str, parts))


def type_name(obj):
    """Fetch the type name of an object.

    This is a cosmetic shortcut.  I find the normal method very ugly.

    :param any obj: The object you want the type name of
    :returns str: The type name

    """
    return type(obj).__name__


def class_name(obj):
    """Fetch the class name of an object (class or instance).

    Another cosmetic shortcut.  The builtin way of getting an instance's class
    name is pretty disgusting (and long), accessing two hidden attributes in
    a row just feels wrong.

    :param any obj: The object you want the class name of
    :returns str: The class name

    """
    if isinstance(obj, type):
        # It's a class.
        return obj.__name__
    else:
        # It's an instance of a class.
        return obj.__class__.__name__


def can_be_index(obj):
    """Determine if an object can be used as the index of a sequence.

    :param any obj: The object to test
    :returns bool: Whether it can be an index or not

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
    :returns bool: Whether it is iterable or not

    """
    try:
        for _ in obj:
            break
    except TypeError:
        return False
    else:
        return True


def is_hashable(obj):
    """Determine if an object is hashable.

    :param any obj: The object to test
    :returns bool: Whether it is hashable or not

    """
    try:
        hash(obj)
    except TypeError:
        return False
    else:
        return True


def find_by_attr(collection, attr, value):
    """Find objects in a collection that have an attribute equal to a value.

    :param iterable collection: The collection to search through
    :param str attr: The attribute to search by
    :param any value: The value to search for
    :returns list: A list of any matching objects

    """
    unset = object()
    matches = []
    for obj in collection:
        match = getattr(obj, attr, unset)
        if match is not unset and (match is value or match == value):
            matches.append(obj)
    return matches


def int_to_base_n(integer, charset):
    """Convert an integer into a base-N string using a given character set.

    :param int integer: The integer to convert
    :param str charset: The character set to use for the conversion
    :returns str: The converted string
    :raises ValueError: If `charset` contains duplicate characters

    """
    if len(charset) > len(set(charset)):
        raise ValueError("character set contains duplicate characters")
    base = len(charset)
    integer = int(integer)
    places = []
    while integer >= base:
        places.append(charset[integer % base])
        integer //= base
    places.append(charset[integer])
    return "".join(reversed(places))


def base_n_to_int(string, charset):
    """Convert a base-N string into an integer using a given character set.

    :param str string: The string to convert
    :param str charset: The character set to use for the conversion
    :returns str: The converted string
    :raises ValueError: If `charset` contains duplicate characters

    """
    if len(charset) > len(set(charset)):
        raise ValueError("character set contains duplicate characters")
    base = len(charset)
    integer = 0
    for index, char in enumerate(reversed(string)):
        integer += charset.index(char) * (base ** index)
    return integer


def generate_hash(string):
    """Generate a cryptographic hash from a string.

    :param str string: A string to generate the hash from
    :return str: The generated hash

    """
    byte_string = string.encode()
    hashed_string = bcrypt.hashpw(byte_string, bcrypt.gensalt())
    return hashed_string.decode()


def check_hash(string, hashed_string):
    """Check that an input string matches a given hash.

    :param str string: The input string
    :param str hashed_string: The hash to compare to
    :return bool: Whether the input string matches the given hash

    """
    byte_string = string.encode()
    byte_hash = hashed_string.encode()
    return bcrypt.hashpw(byte_string, byte_hash) == byte_hash
