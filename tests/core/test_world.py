# -*- coding: utf-8 -*-
"""Tests for world entities."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

import gc

import pytest

from cwmud.core.attributes import Unset
from cwmud.core.players import Player
from cwmud.core.world import Room


class TestRooms:

    """A collection of tests for room entities."""

    room = None

    def test_room_create(self):
        """Test that we can create a room."""
        type(self).room = Room()

    def test_room_coords(self):
        """Test that room coordinates function properly."""
        assert self.room.coords == (Unset, Unset, Unset)
        assert self.room.get_coord_str() == Unset
        self.room.x, self.room.y, self.room.z = (5, 5, 5)
        assert self.room.coords == (5, 5, 5)
        assert self.room.get_coord_str() == "5,5,5"
        with pytest.raises(ValueError):
            self.room.x = "123"
        with pytest.raises(ValueError):
            self.room.y = "123"
        with pytest.raises(ValueError):
            self.room.z = "123"

    def test_room_exits(self):
        """Test that room exits function properly."""
        assert not self.room.get_exits()
        another_room = Room()
        another_room.x, another_room.y, another_room.z = (5, 5, 6)
        assert self.room.get_exits() == {"up": another_room}
        del Room._caches["uid"][another_room.uid]
        del another_room
        gc.collect()
        assert not self.room.get_exits()

    def test_room_chars(self):
        """Test that a room's character list functions properly."""
        assert not self.room.chars
        char = Player()
        char.resume(quiet=True)
        char.room = self.room
        assert set(self.room.chars) == {char}
        char.room = Unset
        assert not self.room.chars

    def test_room_name(self):
        """Test that room names function properly."""
        assert self.room.name == "An Unnamed Room"
        with pytest.raises(ValueError):
            self.room.name = 123
        with pytest.raises(ValueError):
            self.room.name = "x" * 61
        self.room.name = "test room"
        assert self.room.name == "Test Room"

    def test_room_desc(self):
        """Test that room descriptions function properly."""
        assert self.room.description == "A nondescript room."
        with pytest.raises(ValueError):
            self.room.description = 123
        self.room.description = "A boring test room."
        assert self.room.description == "A boring test room."

    def test_movement_strings(self):
        """Test that we can generate movement strings."""
        to_dir, from_dir = self.room.get_movement_strings((1, 0, 0))
        assert to_dir == "east"
        assert from_dir == "the west"
