# -*- coding: utf-8 -*-
"""Tests for session management and client IO."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

import pytest

from cwmud import settings
from cwmud.core.sessions import AlreadyExists, SessionManager
from cwmud.core.shells import EchoShell


class TestSessions:

    """A collection of tests for session management."""

    sessions = None
    session = None
    prompt = ""

    # noinspection PyDocstring
    class _FakeClient:

        def __init__(self, port):
            self.active = True
            self.host = "127.0.0.1"
            self.port = port
            self._idle = 0
            self._commands = []
            self._output = []

        @property
        def command_pending(self):
            return bool(self._commands)

        def get_command(self):
            if self._commands:
                return self._commands.pop(0)

        def get_idle_time(self):
            return self._idle

        def send(self, output):
            return self._output.append(output)

        def close(self):
            self.active = False

    client = _FakeClient(56789)

    def test_session_manager_create(self):
        """Test that we can create a session manager.

        This is currently redundant, importing the sessions package already
        creates one, but we can keep it for symmetry and in case that
        isn't always so.

        """
        type(self).sessions = SessionManager()
        assert self.sessions

    def test_session_create(self):
        """Test that we can create a session."""
        type(self).session = self.sessions.create(self.client)
        assert self.session

    def test_session_create_already_exists(self):
        """Test that trying to create a session with the same client fails."""
        with pytest.raises(AlreadyExists):
            self.sessions.create(self.client)

    def test_session_find_by_client(self):
        """Test that we can find a session by its client."""
        assert self.sessions.find_by_client(self.client) is self.session

    def test_session_active(self):
        """Test that we can determine if a session should be closed."""
        assert self.session.active
        self.session._client = None
        assert not self.session.active
        self.session._client = self.client
        self.session.flags.toggle("closed")
        assert not self.session.active
        self.session.flags.toggle("closed")
        assert self.session.active

    def test_session_host(self):
        """Test that we can get the host address of the session."""
        assert self.session.host

    def test_session_set_shell(self):
        """Test that we can set a session's current shell."""
        self.session.shell = EchoShell()
        assert self.session._shell
        assert isinstance(self.session._shell, EchoShell)
        self.session.shell = None
        assert self.session._shell is None
        with pytest.raises(TypeError):
            self.session.shell = 0
        # Setting it to Shell or one of its subclasses instead of an instance
        # will implicitly instantiate the class and set it to the new instance.
        self.session.shell = EchoShell
        assert self.session._shell
        assert isinstance(self.session._shell, EchoShell)

    def test_session_get_shell(self):
        """Test that we can get a session's current shell."""
        assert self.session.shell
        assert isinstance(self.session.shell, EchoShell)

    def test_session_get_prompt(self):
        """Test that we can generate the prompt for a session."""
        type(self).prompt = self.session._get_prompt()
        assert self.prompt

    def test_session_get_prompt_no_shell(self):
        """Test that a session with no shell returns the default prompt."""
        shell = self.session.shell
        self.session.shell = None
        assert self.session._get_prompt() == "^y>^~ "
        self.session.shell = shell

    def test_session_send(self):
        """Test that we can send output to a session."""
        self.session.send("This", "is a", "test.")
        self.session.send("\n", "t", 10, 8, 2014, sep="\\", end="\r\n")
        assert self.session._output_queue.popleft() == "This is a test.\n"
        assert self.session._output_queue.popleft() == "\n\\t\\10\\8\\2014\r\n"
        assert not self.session._output_queue

    def test_session_parse_input(self):
        """Test that a session can parse input."""
        self.session._parse_input("test")
        self.session._parse_input("beep beep")
        assert self.session._output_queue.popleft() == "You sent: test\n"
        assert self.session._output_queue.popleft() == "You sent: beep beep\n"
        assert not self.session._output_queue

    def test_session_parse_input_unhandled(self):
        """Test that unhandled session input gets logged."""
        shell = self.session.shell
        self.session.shell = None
        self.session._parse_input("test")
        with open(settings.LOG_PATH) as log_file:
            last_line = log_file.readlines()[-1]
            assert "Input not handled" in last_line.rstrip()
        self.session.shell = shell

    def test_session_poll(self):
        """Test that we can poll a session to process its queued IO."""
        self.client._commands.append("test")
        assert self.client.command_pending
        self.session.poll()
        assert not self.client.command_pending
        assert self.client._output.pop(0) == "You sent: test\n"
        assert self.client._output.pop(0) == "\n" + self.prompt
        assert not self.client._output

    def test_session_poll_no_command(self):
        """Test that sending to a session with no input sends a newline."""
        self.session.send("Hello!")
        self.session.poll()
        assert self.client._output.pop(0) == "\nHello!\n"
        assert self.client._output.pop(0) == "\n" + self.prompt
        assert not self.client._output

    def test_session_check_idle(self):
        """Test that we can determine if a session is idle."""
        assert not self.session.flags.has_any("idle", "close")
        self.session._check_idle()
        assert not self.session.flags.has_any("idle", "close")
        # They've gone idle.
        self.client._idle = settings.IDLE_TIME
        self.session._check_idle()
        assert "idle" in self.session.flags
        assert "close" not in self.session.flags
        assert (self.session._output_queue.popleft() ==
                "You are whisked away into the void.\n")
        # They came back.
        self.client._idle = 0
        self.session._check_idle()
        assert not self.session.flags.has_any("idle", "close")
        assert (self.session._output_queue.popleft() ==
                "You have returned from the void.\n")
        assert self.session.active
        # Now they've been idle for a really long time.
        self.client._idle = settings.IDLE_TIME_MAX
        self.session._check_idle()
        assert self.session.flags.has("close")
        assert (self.session._output_queue.popleft() ==
                "^RDisconnecting due to inactivity. Goodbye!^~\n")

    def test_session_manager_poll(self):
        """Test that we can poll a session manager to poll all its sessions."""
        # Create a couple more sessions to test with.
        sessions = [self.session,
                    self.sessions.create(self._FakeClient(56790), EchoShell),
                    self.sessions.create(self._FakeClient(56791), EchoShell)]
        # Change them around a bit and then poll them all.
        sessions[0]._client._commands.append("test")
        sessions[1]._client._commands.append("test")
        self.sessions.poll()
        # The first session was flagged for closing in the previous test,
        # so its input should have been ignored and its flag should have
        # been changed from close to closed.
        assert sessions[0]._client.command_pending
        assert not sessions[0]._client._output
        assert not sessions[0].active
        assert "closed" in sessions[0].flags
        # The second session should have been parsed and output returned.
        assert not sessions[1]._client.command_pending
        assert sessions[1]._client._output.pop(0) == "You sent: test\n"
        assert sessions[1]._client._output.pop(0) == "\n" + self.prompt
        assert not sessions[1]._client._output
        assert sessions[1].active
        # And the third session didn't do anything, so should be unchanged.
        assert not sessions[2]._client.command_pending
        assert not sessions[2]._client._output
        assert sessions[2].active

    def test_session_close(self):
        """Test that we can close a session."""
        assert len(self.sessions._sessions) == 3
        session = self.sessions._sessions[56791]
        assert session.active
        session.close("bye cause reasons.")
        session.poll()
        assert not session.active
        assert session._output_queue.popleft() == "bye cause reasons.\n"
        assert not session._output_queue

    def test_session_manager_prune(self):
        """Test that we can prune the dead sessions from a session manager."""
        assert len(self.sessions._sessions) == 3
        self.sessions.prune()
        assert len(self.sessions._sessions) == 1
