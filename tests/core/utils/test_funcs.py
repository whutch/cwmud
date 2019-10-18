# -*- coding: utf-8 -*-
"""Tests for miscellaneous utility functions."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2017 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

import string

import pytest

from cwmud.core import utils


# Tests for the 'joins' string joining utility function.

def test_joins_nothing():
    """Test that joining nothing gets us nothing."""
    assert utils.joins() == ""


def test_joins_strings():
    """Test that we can join some strings."""
    assert utils.joins("this ", "is a", "test") == "this  is a test"


def test_joins_non_strings():
    """Test that we can join both strings and non-strings."""
    assert utils.joins("test", "number", 3) == "test number 3"


def test_joins_empty_strings():
    """Test that it won't bother joining a sequence of empty strings."""
    assert utils.joins("", "", "") == ""


def test_joins_given_separator():
    """Test that we can join with a given separator."""
    assert utils.joins(10, 2, 2014, sep="/") == "10/2/2014"


# Tests for the rest of the utility functions.

def test_type_name():
    """Test that we can get a type name."""
    assert utils.type_name("test") == "str"


def test_class_name():

    """Test that we can get a class name.

    The name of an instance of a class should be the same as the class itself.

    """

    class _TestClass:
        pass

    instance = _TestClass()

    assert (utils.class_name(_TestClass)
            == utils.class_name(instance)
            == "_TestClass")


def test_can_be_index():
    """Test that we can determine if an object can be used as an index."""
    assert utils.can_be_index(0) is True
    assert utils.can_be_index("no") is False


def test_is_iterable():
    """Test that we can determine if an object is iterable."""
    assert utils.is_iterable("test") is True
    assert utils.is_iterable([1, 2, 3]) is True
    assert utils.is_iterable({}) is True
    assert utils.is_iterable(0) is False


def test_is_hashable():
    """Test that we can determine if an object is hashable."""
    assert utils.is_hashable("test") is True
    assert utils.is_hashable(0) is True
    assert utils.is_hashable((1, 2)) is True
    assert utils.is_hashable([1, 2]) is False
    assert utils.is_hashable({"1": 2}) is False


def test_find_by_attr():

    """Test that we can find an object in a collection by attribute."""

    class _TestClass:

        def __init__(self, value):
            self.value = value

    instances = [_TestClass(n) for n in (1, 1, 2, 3, 4, 4, 4)]

    assert utils.find_by_attr(instances, "value", 0) == []
    assert utils.find_by_attr(instances, "value", 2)
    assert len(utils.find_by_attr(instances, "value", 1)) == 2
    assert len(utils.find_by_attr(instances, "value", 4)) == 3
    assert not utils.find_by_attr(instances, "fake_value", None)


def test_int_to_base_n():

    """Test that we can convert an integer to a base-N string."""

    # Test for duplicate characters in the character set.
    with pytest.raises(ValueError):
        assert utils.int_to_base_n(1337, "lololol")

    assert utils.int_to_base_n(123, "01") == "1111011"
    assert utils.int_to_base_n(555, string.octdigits) == "1053"
    assert utils.int_to_base_n(48879, string.hexdigits[:16]) == "beef"


def test_base_n_to_int():

    """Test that we can convert a base-N string to an integer."""

    # Test for duplicate characters in the character set.
    with pytest.raises(ValueError):
        assert utils.base_n_to_int("nope", "lololol")

    assert utils.base_n_to_int("1111011", "01") == 123
    assert utils.base_n_to_int("1053", string.octdigits) == 555
    assert utils.base_n_to_int("beef", string.hexdigits[:16]) == 48879
