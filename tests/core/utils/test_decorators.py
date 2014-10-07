# -*- coding: utf-8 -*-
"""Tests for support decorators."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from atria.core.utils.decorators import weak_property


class TestWeakProperty:

    """A collection of tests for weak properties."""

    class _TestClass:

        instances = 0

        def __init__(self):
            type(self).instances += 1

        def __del__(self):
            type(self).instances -= 1

        @weak_property
        def weak_ref(self):
            """Set a weak reference to something."""
            pass

    def test_single_ref(self):
        """Test linking an object to another through a weak property."""
        assert self._TestClass.instances == 0
        one = self._TestClass()
        two = self._TestClass()
        assert self._TestClass.instances == 2
        one.weak_ref = two
        assert one.weak_ref is two
        del two
        assert not one.weak_ref
        assert self._TestClass.instances == 1

    def test_double_ref(self):
        """Test linking two objects to each other through weak properties."""
        assert self._TestClass.instances == 0
        one = self._TestClass()
        two = self._TestClass()
        assert self._TestClass.instances == 2
        one.weak_ref = two
        two.weak_ref = one
        assert one.weak_ref is two and two.weak_ref is one
        del one
        del two
        assert self._TestClass.instances == 0

    def test_self_ref(self):
        """Test linking an object to itself through a weak property."""
        assert self._TestClass.instances == 0
        one = self._TestClass()
        assert self._TestClass.instances == 1
        one.weak_ref = one
        assert one.weak_ref is one
        del one
        assert self._TestClass.instances == 0
