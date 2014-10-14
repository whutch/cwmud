# -*- coding: utf-8 -*-
"""Tests for mix-in support classes."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

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
        assert not "test" in self.instance.flags

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

        instances = 0

        def __init__(self):
            super().__init__()
            type(self).instances += 1

        def __del__(self):
            type(self).instances -= 1

        @property
        def weak_ref(self):
            """Get this object's weak reference."""
            return self._get_weak("weak_ref")

        @weak_ref.setter
        def weak_ref(self, obj):
            """Set this object's weak reference.

            :param any obj: The object we want to weakly reference
            :returns: None

            """
            self._set_weak("weak_ref", obj)

    def test_weak_ref_one_way(self):
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

    def test_weak_ref_both_ways(self):
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

    def test_weak_ref_to_self(self):
        """Test linking an object to itself through a weak property."""
        assert self._TestClass.instances == 0
        one = self._TestClass()
        assert self._TestClass.instances == 1
        one.weak_ref = one
        assert one.weak_ref is one
        del one
        assert self._TestClass.instances == 0


class TestHasParent:

    """A collection of tests for parents mix-in class."""

    class _TestClass(HasFlags, HasParent):

        def __init__(self):
            super().__init__()
            self.some_attribute = 5

    grandparent = _TestClass()
    parent = _TestClass()
    child = _TestClass()

    def test_get_parent(self):
        """Test that we can get the parent of an object."""
        assert self.child.parent is None

    def test_set_parent(self):
        """Test that we can set the parent of an object."""
        self.child.parent = self.parent
        assert self.child.parent is self.parent
        self.parent.parent = self.grandparent
        assert self.parent.parent is self.grandparent
        assert self.child.parent.parent is self.grandparent

    def test_set_parent_invalid_parent(self):
        """Test that trying to set an invalid parent fails."""
        with pytest.raises(TypeError):
            self.grandparent.parent = "yeah"

    def test_set_parent_circular(self):
        """Test that trying to set a circular lineage fails."""
        assert not self.grandparent.parent
        with pytest.raises(ValueError):
            self.grandparent.parent = self.child
        assert not self.grandparent.parent

    def test_get_lineage(self):
        """Test that we can get an objects lineage through the parents."""
        assert (tuple(self.child.get_lineage()) ==
                (self.child, self.parent, self.grandparent))

    def test_get_lineage_higher_priority(self):
        """Test that we can get the higher priority objects in a lineage."""
        assert (tuple(self.child.get_lineage(priority=1)) == ())

    def test_get_lineage_lower_priority(self):
        """Test that we can get the lower priority objects in a lineage."""
        assert (tuple(self.child.get_lineage(priority=-1)) ==
                (self.parent, self.grandparent))

    def test_get_lineage_parent_first(self):
        """Test that we can get an objects lineage with a parent first flag."""
        self.child.flags.add("parent first")
        assert (tuple(self.child.get_lineage()) ==
                (self.parent, self.grandparent, self.child))
        assert (tuple(self.child.get_lineage(priority=1)) ==
                (self.parent, self.grandparent))
        assert (tuple(self.child.get_lineage(priority=-11)) == ())

    def test_get_ancestors(self):
        """Test that we can get the ancestors of an object."""
        assert (tuple(self.child.get_ancestors()) ==
                (self.parent, self.grandparent))

    def test_has_ancestor(self):
        """Test that we can see if an object has an ancestor."""
        assert self.child.has_ancestor(self.grandparent)
        assert not self.grandparent.has_ancestor(self.child)

    def test_unset_parent(self):
        """Test that we can unset the parent of an object."""
        self.child.parent = None
        assert self.child.parent is None
        # And just for the hell of it..
        self.grandparent.parent = self.child
        assert self.parent.parent.parent is self.child
