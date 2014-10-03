# -*- coding: utf-8 -*-
"""Tests for miscellaneous utility functions"""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from atria.core.utils import funcs


# Tests for the 'joins' string joining utility function

def test_joins_nothing():
    """Test that joining nothing gets us nothing."""
    assert funcs.joins() == ""


def test_joins_strings():
    """Test that we can join some strings."""
    assert funcs.joins("this ", "is a", "test") == "this  is a test"


def test_joins_non_strings():
    """Test that we can join both strings and non-strings."""
    assert funcs.joins("test", "number", 3) == "test number 3"


def test_joins_empty_strings():
    """Test that it won't bother joining a sequence of empty strings."""
    assert funcs.joins("", "", "") == ""


def test_joins_given_separator():
    """Test that we can join with a given separator."""
    assert funcs.joins(10, 2, 2014, sep="/") == "10/2/2014"


# Tests for the rest of the utility functions

def test_type_name():
    """Test that we can get a type name."""
    assert funcs.type_name("test") == "str"


def test_class_name():

    """Test that we can get a class name.

    The name of an instance of a class should be the same as the class itself.

    """

    class _TestClass:
        pass

    test_instance = _TestClass()

    assert (funcs.class_name(_TestClass) ==
            funcs.class_name(test_instance) ==
            "_TestClass")


def test_can_be_index():
    """Test that we can determine if an object can be used as an index."""
    assert funcs.can_be_index(0) is True
    assert funcs.can_be_index("no") is False


def test_is_iterable():
    """Test that we can determine if an object is iterable."""
    assert funcs.is_iterable("test") is True
    assert funcs.is_iterable([1, 2, 3]) is True
    assert funcs.is_iterable(0) is False


def test_is_hashable():
    """Test that we can determine if an object is hashable."""
    assert funcs.is_hashable("test") is True
    assert funcs.is_hashable(0) is True
    assert funcs.is_hashable((1, 2)) is True
    assert funcs.is_hashable([1, 2]) is False
    assert funcs.is_hashable({"1": 2}) is False
