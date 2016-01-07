# -*- coding: utf-8 -*-
"""Tests for character entities."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

import pytest

from atria.core.accounts import Account
from atria.core.characters import (Character, CharacterName, create_character,
                                   RequestNewCharacterName)
from atria.core.entities import Unset
from atria.core.utils.funcs import joins
from atria.core.world import Room


class _FakeSession:

    def __init__(self):
        self._output = []
        self._request_queue = []

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


@pytest.fixture(scope="module")
def room():
    """Create a Room instance for all tests to share."""
    return Room(savable=False)


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
