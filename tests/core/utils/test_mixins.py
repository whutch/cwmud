# -*- coding: utf-8 -*-
"""Tests for mix-in support classes."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from atria.core.utils.mixins import HasFlags


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

    def test_all_flags(self):
        """Test that the all property returns the current flags."""
        assert set(self.instance.flags.all) == {"test", 1, 2}

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
