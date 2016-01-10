# -*- coding: utf-8 -*-
"""Tests for character entities."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from collections import deque
import pytest

from atria.core.accounts import Account
from atria.core.characters import (Character, CharacterName, create_character,
                                   RequestNewCharacterName)
from atria.core.entities import Unset
from atria.core.utils.funcs import joins
from atria.core.world import Room


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
def account():
    """Create an Account instance for all tests to share."""
    return Account(savable=False)


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
    _character.name = "Target"
    _character.session = _other_session
    return _character


@pytest.fixture(scope="module")
def room():
    """Create a Room instance for all tests to share."""
    return Room({"x": 0, "y": 0, "z": 0}, savable=False)


@pytest.fixture(scope="module")
def other_room():
    """Create another Room instance for all tests to share."""
    _room = Room({"x": 1, "y": 0, "z": 0}, savable=False)
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

    def test_character_account(self, character, account):
        """Test that we can set a character's account."""
        assert character.account is Unset
        with pytest.raises(ValueError):
            character.account = "test"
        character.account = account
        character.session.account = account
        assert character.account is account

    def test_character_room(self, character, room):
        """Test that we can set a character's room."""
        assert character.room is Unset
        with pytest.raises(ValueError):
            character.room = "test"
        assert not character.active
        character.room = room
        assert character not in room.chars
        character.active = True
        character.room = Unset
        assert character not in room.chars
        character.room = room
        assert character.room is room
        assert character in room.chars

    def test_character_name(self, character):
        """Test that we can set a character's name."""
        assert character.name is Unset
        with pytest.raises(ValueError):
            character.name = "123"  # Invalid
        with pytest.raises(ValueError):
            character.name = "a"  # Too short
        with pytest.raises(ValueError):
            character.name = "a"*20  # Too long
        CharacterName.RESERVED.append("Nope")
        with pytest.raises(ValueError) as exc:
            character.name = "nope"
        assert exc.exconly().endswith("reserved.")
        character.name = "testing"
        assert character.name == "Testing"
        with pytest.raises(ValueError) as exc:
            character.name = "testing"
        assert exc.exconly().endswith("already in use.")

    def test_character_name_request(self, character):
        """Test that we can validate a character name request."""
        request = RequestNewCharacterName(character.session, None)
        with pytest.raises(request.ValidationFailed):
            request._validate("123")
        assert request._validate("moretesting") == "Moretesting"

    def test_character_suspend(self, character, room):
        """Test that we can suspend a character."""
        assert character.active
        assert character in room.chars
        character.suspend()
        assert not character.active
        assert character not in room.chars

    def test_character_resume(self, character, room):
        """Test that we can resume a character."""
        assert not character.active
        assert character not in room.chars
        character.resume(quiet=True)
        assert character.active
        assert character in room.chars

    def test_character_suspend_no_room(self, character):
        """Test that we can suspend a character with no room."""
        character.room = Unset
        assert character.active
        character.suspend()
        assert not character.active

    def test_character_resume_no_room(self, character):
        """Test that we can resume a character with no room."""
        assert character.room is Unset
        assert not character.active
        character.resume()
        assert character.active

    def test_character_act(self, character, other_character):
        """Test that we can generate 'act' messages for a character."""
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
                "Testing explodes, hard.\n")
        # Generate messages for the source and the target.
        character.act("{s} hit{ss} {t} in the face!", target=other_character)
        assert (character.session._output.pop() ==
                "You hit Target in the face!\n")
        assert (other_character.session._output.pop() ==
                "Testing hits you in the face!\n")
        character.act("{s} speak{ss} gibberish for a moment.",
                      to=Character.all())
        assert (character.session._output.pop() ==
                "You speak gibberish for a moment.\n")
        assert (other_character.session._output.pop() ==
                "Testing speaks gibberish for a moment.\n")
        character.act("{s} does something to {t}.", target=other_character,
                      to=Character.all(), and_self=False)
        assert not character.session._output
        assert (other_character.session._output.pop() ==
                "Testing does something to you.\n")

    def test_character_show_room(self, character, room, other_room):
        """Test that we can generate a room display for a character."""
        _session = character.session
        character.session = None
        character.show_room(room)
        assert not _session._output
        character.session = _session
        assert not character.room
        character.show_room()
        assert not character.session._output
        character.room = room
        character.show_room()
        assert "An Unnamed Room" in character.session._output.popleft()
        assert "Exits:" in character.session._output.popleft()
        assert character.room is not other_room
        character.show_room(other_room)
        assert "Another Room" in character.session._output.popleft()
        assert "Exits:" in character.session._output.popleft()
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
        assert "Exits:" in character.session._output.popleft()
        other_character.room = room
        character.move_to_room(other_room, *msgs)
        assert "You leave." in character.session._output.popleft()
        assert "Another Room" in character.session._output.popleft()
        assert "Exits" in character.session._output.popleft()
        assert "Testing leaves." in other_character.session._output.popleft()
        character.move_to_room(room, *msgs)
        assert "You leave." in character.session._output.popleft()
        assert "An Unnamed Room" in character.session._output.popleft()
        assert "Exits" in character.session._output.popleft()
        assert "Testing arrives." in other_character.session._output.popleft()

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

    def test_character_serialization(self, character, room):
        """Test that character serialization functions properly."""
        character.room = room
        data = character.serialize()
        assert data
        assert data["room"] == room.key
        new_room = Room(savable=False)
        data["room"] = new_room.key
        character.deserialize(data)
        assert character.room is new_room

    def test_character_creation(self, session, account):

        """Test that character creation functions properly."""

        session.account = account

        def _callback(session, character):
            assert not session._request_queue
            assert character
            assert character.name == "Moretesting"
            assert character.account is account
            assert character._savable
            character._savable = False

        assert not session._request_queue
        create_character(session, _callback)
        assert session._request_queue
        request = session._request_queue.pop()
        assert isinstance(request, RequestNewCharacterName)
        assert not request.resolve("moretesting")  # Must confirm name.
        assert request.resolve("yes")
