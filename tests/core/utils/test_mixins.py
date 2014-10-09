# -*- coding: utf-8 -*-
"""Tests for mix-in support classes."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

import pytest

from atria.core.utils.mixins import HasFlags, HasParent


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

    def test_get_lineage_parent_first(self):
        """Test that we can get an objects lineage with a parent first flag."""
        self.child.flags.add("parent first")
        assert (tuple(self.child.get_lineage()) ==
                (self.parent, self.grandparent, self.child))
