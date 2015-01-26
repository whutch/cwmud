# -*- coding: utf-8 -*-
"""Tests for mix-in support classes."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2015 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

import gc
from weakref import finalize

import pytest

from atria.core.utils.mixins import HasFlags, HasParent, HasWeaks


class TestHasFlags:

    """A collection of tests for the flagging mix-in class."""

    class _TestClass(HasFlags):

        def __init__(self):
            super().__init__()
            self.some_attribute = 5

    instance = _TestClass()

    def test_flags_property(self):
        """Test that the flags property returns a flag set."""
        assert hasattr(self.instance.flags, "toggle")

    def test_contains_flag(self):
        """Test that we can check if the set contains a flag."""
        assert "test" not in self.instance.flags

    def test_add_flag(self):
        """Test that we can add one flag to the flag set."""
        self.instance.flags.add("test")
        assert "test" in self.instance.flags

    def test_add_multiple_flags(self):
        """Test that we can add multiple flags at once."""
        self.instance.flags.add(1, 2)
        assert 1 in self.instance.flags and 2 in self.instance.flags

    def test_flags_as_tuple(self):
        """Test that the all property returns the current flags."""
        assert set(self.instance.flags.as_tuple) == {"test", 1, 2}

    def test_iter_flags(self):
        """Test that we can iterate through the flag set."""
        assert {flag for flag in self.instance.flags} == {"test", 1, 2}

    def test_drop_flag(self):
        """Test that we can drop one flag from the flag set."""
        assert "test" in self.instance.flags
        self.instance.flags.drop("test")
        assert "test" not in self.instance.flags

    def test_drop_multiple_flags(self):
        """Test that we can drop multiple flags at once."""
        assert 1 in self.instance.flags and 2 in self.instance.flags
        self.instance.flags.drop(1, 2)
        assert 1 not in self.instance.flags and 2 not in self.instance.flags

    def test_toggle_flags(self):
        """Test that we can toggle one flag in the flag set."""
        assert "test" not in self.instance.flags
        self.instance.flags.toggle("test")
        assert "test" in self.instance.flags

    def test_toggle_multiple_flags(self):
        """Test that we can toggle multiple flags at once."""
        assert "test" in self.instance.flags
        assert 1 not in self.instance.flags and 2 not in self.instance.flags
        self.instance.flags.toggle("test", 1, 2)
        assert "test" not in self.instance.flags
        assert 1 in self.instance.flags and 2 in self.instance.flags

    def test_flags_as_bool(self):
        """Test that we can use the flag set in a boolean statement."""
        assert self.instance.flags
        self.instance.flags.toggle(1, 2)
        assert not self.instance.flags

    def test_has_flag(self):
        """Test that we can check for a flag through the has method."""
        assert not self.instance.flags.has("test")
        self.instance.flags.toggle("test")
        assert self.instance.flags.has("test")

    def test_has_multiple_flags(self):
        """Test that we can check for multiple flags through the has method."""
        assert not self.instance.flags.has("test", 1, 2)
        self.instance.flags.toggle(1, 2)
        assert self.instance.flags.has("test", 1, 2)

    def test_has_any_flags(self):
        """Test that we can check for flags through the has_any method."""
        assert not self.instance.flags.has_any("nope", 3, 4)
        assert self.instance.flags.has_any("test", 3, 4)


class TestHasWeaks:

    """A collection of tests for weak properties."""

    class _TestClass(HasWeaks):

        count = 0

        def __init__(self):
            super().__init__()
            type(self).count += 1
            finalize(self, type(self)._dec_count)

        @classmethod
        def _dec_count(cls):
            cls.count -= 1

        @property
        def weak_ref(self):
            """Get this object's weak reference."""
            return self._get_weak("weak_ref")

        @weak_ref.setter
        def weak_ref(self, obj):
            """Set this object's weak reference.

            :param any obj: The object we want to weakly reference
            :returns None:

            """
            self._set_weak("weak_ref", obj)

    def test_weak_ref_one_way(self):
        """Test linking an object to another through a weak property."""
        assert self._TestClass.count == 0
        one = self._TestClass()
        two = self._TestClass()
        assert self._TestClass.count == 2
        one.weak_ref = two
        assert one.weak_ref is two
        del two
        gc.collect()
        assert not one.weak_ref
        assert self._TestClass.count == 1
        del one
        gc.collect()
        assert self._TestClass.count == 0

    def test_weak_ref_both_ways(self):
        """Test linking two objects to each other through weak properties."""
        assert self._TestClass.count == 0
        one = self._TestClass()
        two = self._TestClass()
        assert self._TestClass.count == 2
        one.weak_ref = two
        two.weak_ref = one
        assert one.weak_ref is two and two.weak_ref is one
        del one
        del two
        gc.collect()
        assert self._TestClass.count == 0

    def test_weak_ref_to_self(self):
        """Test linking an object to itself through a weak property."""
        assert self._TestClass.count == 0
        one = self._TestClass()
        assert self._TestClass.count == 1
        one.weak_ref = one
        assert one.weak_ref is one
        del one
        gc.collect()
        assert self._TestClass.count == 0


class TestHasParent:

    """A collection of tests for parents mix-in class."""

    class _A(HasParent):
        pass

    class _B(_A):
        pass

    class _C(_B):
        pass

    class _D(_B):
        pass

    class _E(_C, _D):
        pass

    def test_get_lineage(self):
        """Test that we can get an objects lineage through the parents."""
        assert (tuple(self._C.get_lineage()) ==
                (self._C, self._B, self._A))

    def test_get_lineage_higher_priority(self):
        """Test that we can get the higher priority objects in a lineage."""
        assert (tuple(self._C.get_lineage(priority=1)) == ())

    def test_get_lineage_lower_priority(self):
        """Test that we can get the lower priority objects in a lineage."""
        assert (tuple(self._C.get_lineage(priority=-1)) ==
                (self._B, self._A))

    def test_get_lineage_parent_first(self):
        """Test that we can get an objects lineage with a parent first flag."""
        self._C.parent_first = True
        assert (tuple(self._C.get_lineage()) ==
                (self._B, self._A, self._C))
        assert (tuple(self._C.get_lineage(priority=1)) ==
                (self._B, self._A))
        assert (tuple(self._C.get_lineage(priority=-1)) == ())

    def test_get_ancestors(self):
        """Test that we can get the ancestors of an object."""
        assert (tuple(self._C.get_ancestors()) ==
                (self._B, self._A))
        assert tuple(self._A.get_ancestors()) == ()

    def test_has_ancestor(self):
        """Test that we can see if an object has an ancestor."""
        assert self._C.has_ancestor(self._A)
        assert not self._A.has_ancestor(self._C)
