# -*- coding: utf-8 -*-
"""Tests for player entities."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from collections import deque
import pytest

from cwmud.core.accounts import Account
from cwmud.core.attributes import Unset
from cwmud.core.players import (create_player, Player, PlayerName,
                                RequestNewPlayerName)
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
def account():
    """Create an Account instance for all tests to share."""
    return Account(savable=False)


@pytest.fixture(scope="module")
def player():
    """Create a Player instance for all tests to share."""
    _player = Player(savable=False)
    _player.active = True
    return _player


@pytest.fixture(scope="module")
def room():
    """Create a Room instance for all tests to share."""
    return Room({"x": 6, "y": 4, "z": 4}, savable=False)


@pytest.fixture(scope="module")
def session():
    """Create a session for all tests to share."""
    return _FakeSession()


class TestPlayers:

    """A collection of tests for player entities."""

    def test_player_create(self):
        """Test that we can create a new player instance."""
        assert Player()

    def test_player_account(self, player, session, account):
        """Test that we can set a player's account."""
        player.session = session
        assert player.account is Unset
        with pytest.raises(ValueError):
            player.account = "test"
        player.account = account
        player.session.account = account
        assert player.account is account

    def test_player_name(self, player):
        """Test that we can set a player's name."""
        assert player.name is Unset
        with pytest.raises(ValueError):
            player.name = "123"  # Invalid
        with pytest.raises(ValueError):
            player.name = "a"  # Too short
        with pytest.raises(ValueError):
            player.name = "a" * 20  # Too long
        PlayerName.RESERVED.append("Nope")
        with pytest.raises(ValueError) as exc:
            player.name = "nope"
        assert exc.exconly().endswith("reserved.")
        player.name = "testing"
        assert player.name == "Testing"
        with pytest.raises(ValueError) as exc:
            player.name = "testing"
        assert exc.exconly().endswith("already in use.")

    def test_player_name_request(self, player):
        """Test that we can validate a player name request."""
        request = RequestNewPlayerName(player.session, None)
        with pytest.raises(request.ValidationFailed):
            request._validate("123")
        assert request._validate("moretesting") == "Moretesting"

    def test_player_suspend(self, player, room):
        """Test that we can suspend a player."""
        player.room = room
        assert player.active
        assert player in room.chars
        player.suspend()
        assert not player.active
        assert player not in room.chars

    def test_player_resume(self, player, room):
        """Test that we can resume a player."""
        assert not player.active
        assert player not in room.chars
        player.resume(quiet=True)
        assert player.active
        assert player in room.chars

    def test_player_suspend_no_room(self, player):
        """Test that we can suspend a player with no room."""
        player.room = Unset
        assert player.active
        player.suspend()
        assert not player.active

    def test_player_resume_no_room(self, player):
        """Test that we can resume a player with no room."""
        assert player.room is Unset
        assert not player.active
        player.resume()
        assert player.active

    def test_player_creation(self, session, account):

        """Test that player creation functions properly."""

        session.account = account

        def _callback(session, player):
            assert not session._request_queue
            assert player
            assert player.name == "Moretesting"
            assert player.account is account
            assert player._savable
            player._savable = False

        assert not session._request_queue
        create_player(session, _callback)
        assert session._request_queue
        request = session._request_queue.pop()
        assert isinstance(request, RequestNewPlayerName)
        assert not request.resolve("moretesting")  # Must confirm name.
        assert request.resolve("yes")
