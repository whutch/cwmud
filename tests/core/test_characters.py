# -*- coding: utf-8 -*-
"""Tests for character entities."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from collections import deque
import pytest

from cwmud.core.attributes import Unset
from cwmud.core.characters import Character
from cwmud.core.utils.funcs import joins
from cwmud.core.world import Room


class _FakeSession:

    def __init__(self):
        self.account = None
        self._output = deque()
        self._request_queue = deque()

    def send(self, data, *more, sep=" ", end="\n"):
        return self._output.append(joins(data, *more, sep=sep) + end)

    def request(self, request_class, callback, **options):
        new_request = request_class(self, callback, **options)
        self._request_queue.append(new_request)


@pytest.fixture(scope="module")
def character():
    """Create a Character instance for all tests to share."""
    return Character(savable=False)


# Character.session is a weak property, so we have to define the
# session outside the property assignment so it hangs around.
_other_session = _FakeSession()


@pytest.fixture(scope="module")
def other_character():
    """Create another Character instance for all tests to share."""
    _character = Character(savable=False)
    _character.active = True
    _character.session = _other_session
    return _character


@pytest.fixture(scope="module")
def room():
    """Create a Room instance for all tests to share."""
    return Room({"x": 4, "y": 4, "z": 4}, savable=False)


@pytest.fixture(scope="module")
def other_room():
    """Create another Room instance for all tests to share."""
    _room = Room({"x": 5, "y": 4, "z": 4}, savable=False)
    _room.name = "Another Room"
    return _room


@pytest.fixture(scope="module")
def session():
    """Create a session for all tests to share."""
    return _FakeSession()


class TestCharacters:

    """A collection of tests for character entities."""

    def test_character_create(self):
        """Test that we can create a new character instance."""
        assert Character()

    def test_character_session(self, character, session):
        """Test that we can set a character's session."""
        character.session = session
        assert character.session is session

    def test_character_room(self, character, room):
        """Test that we can set a character's room."""
        assert character.room is Unset
        with pytest.raises(ValueError):
            character.room = "test"
        character.room = room
        assert character in room.chars
        character.room = Unset
        assert character not in room.chars
        character.room = room
        assert character.room is room
        assert character in room.chars

    def test_character_act(self, character, other_character):
        """Test that we can generate 'act' messages for a character."""
        character.active = True
        assert not character.session._output
        assert not other_character.session._output
        # Generate messages for neither the source nor the target.
        character.act("a tree falls and nobody is around.", and_self=False)
        assert not character.session._output
        assert not other_character.session._output
        # Generate messages for the source but not the target.
        character.act("{s} dance{ss} {x} jigs.", context={"x": "five"})
        assert character.session._output
        assert character.session._output.pop() == "You dance five jigs.\n"
        assert not other_character.session._output
        # Generate messages for the target but not the source.
        character.act("{s} explode{ss}, hard.", target=other_character,
                      and_self=False)
        assert not character.session._output
        assert other_character.session._output
        assert (other_character.session._output.pop() ==
                "Unnamed explodes, hard.\n")
        # Generate messages for the source and the target.
        character.act("{s} hit{ss} {t} in the face!", target=other_character)
        assert (character.session._output.pop() ==
                "You hit Unnamed in the face!\n")
        assert (other_character.session._output.pop() ==
                "Unnamed hits you in the face!\n")
        character.act("{s} speak{ss} gibberish for a moment.",
                      to=Character.all())
        assert (character.session._output.pop() ==
                "You speak gibberish for a moment.\n")
        assert (other_character.session._output.pop() ==
                "Unnamed speaks gibberish for a moment.\n")
        character.act("{s} does something to {t}.", target=other_character,
                      to=Character.all(), and_self=False)
        assert not character.session._output
        assert (other_character.session._output.pop() ==
                "Unnamed does something to you.\n")

    def test_character_show_room(self, character, room, other_room):
        """Test that we can generate a room display for a character."""
        _session = character.session
        character.session = None
        character.room = Unset
        character.show_room(room)
        assert not _session._output
        character.session = _session
        character.show_room()
        assert not character.session._output
        character.room = room
        character.show_room()
        assert "An Unnamed Room" in character.session._output.popleft()
        assert character.session._output.popleft()  # The description
        assert "Exits:" in character.session._output.popleft()
        assert character.room is not other_room
        character.show_room(other_room)
        assert "Another Room" in character.session._output.popleft()
        assert character.session._output.popleft()  # The description
        assert "Exits:" in character.session._output.popleft()
        assert not character.session._output
        character.room = Unset

    def test_character_show_exits(self, character, room, other_room):
        """Test that we can generate an exit display for a character."""
        _session = character.session
        character.session = None
        character.show_exits(room)
        assert not _session._output
        character.session = _session
        assert not character.room
        character.show_exits()
        assert not character.session._output
        character.room = room
        character.show_exits()
        exits = character.session._output.popleft()
        assert "Exits:" in exits
        assert "east" in exits
        assert "[Exits:" not in exits
        assert character.room is not other_room
        character.show_exits(other_room, short=True)
        assert "[Exits: west" in character.session._output.popleft()
        assert not character.session._output
        character.room = Unset

    def test_character_move_to_room(self, character, other_character,
                                    room, other_room):
        """Test that we can move a character to a room."""
        with pytest.raises(TypeError):
            character.move_to_room(None)
        msgs = ["{s} leave{ss}.", "{s} arrive{ss}."]
        assert not character.room
        character.move_to_room(room, *msgs)
        # They had no room to leave from, so no departure message.
        assert "An Unnamed Room" in character.session._output.popleft()
        assert character.session._output.popleft()  # The description
        assert "Exits:" in character.session._output.popleft()
        other_character.room = room
        character.move_to_room(other_room, *msgs)
        assert "You leave." in character.session._output.popleft()
        assert "Another Room" in character.session._output.popleft()
        assert character.session._output.popleft()  # The description
        assert "Exits" in character.session._output.popleft()
        assert "Unnamed leaves." in other_character.session._output.popleft()
        character.move_to_room(room, *msgs)
        assert "You leave." in character.session._output.popleft()
        assert "An Unnamed Room" in character.session._output.popleft()
        assert character.session._output.popleft()  # The description
        assert character.session._output.popleft()  # Character list
        assert "Exits" in character.session._output.popleft()
        assert "Unnamed arrives." in other_character.session._output.popleft()

    def test_character_move_direction(self, character, room, other_room):
        """Test that we can move a character in a direction."""
        character.room = Unset
        character.move_direction(1, 0, 0)
        assert not character.room
        character.room = room
        character.move_direction()
        assert character.room is room
        character.move_direction(0, 1, 0)
        assert character.room is room
        assert "can't go that way" in character.session._output.popleft()
        character.move_direction(1, 0, 0)
        assert character.room is other_room

    def test_character_serialization(self, character, room, other_room):
        """Test that character serialization functions properly."""
        character.room = room
        data = character.serialize()
        assert data
        assert data["room"] == room.uid
        data["room"] = other_room.uid
        character.deserialize(data)
        assert character.room is other_room
