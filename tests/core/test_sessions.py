# -*- coding: utf-8 -*-
"""Tests for session management and client IO."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

import pytest

from atria import settings
from atria.core.sessions import AlreadyExists, SessionManager
from atria.core.shells import EchoShell


class TestSessions:

    """A collection of tests for session management."""

    sessions = None
    session = None
    prompt = ""

    # noinspection PyDocstring
    class _FakeSocket:

        def __init__(self):
            self.active = True
            self._idle = 0
            self._commands = []
            self._output = []

        @staticmethod
        def addrport():
            return "127.0.0.1:56789"

        @property
        def cmd_ready(self):
            return bool(self._commands)

        def get_command(self):
            if self._commands:
                return self._commands.pop(0)

        def idle(self):
            return self._idle

        def send_cc(self, output):
            return self._output.append(output)

        # noinspection PyPep8Naming,PyDocstring
        class sock:

            @staticmethod
            def close():
                pass

    socket = _FakeSocket()

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
        type(self).session = self.sessions.create(self.socket)
        assert self.session

    def test_session_create_already_exists(self):
        """Test that trying to create a session with the same socket fails."""
        with pytest.raises(AlreadyExists):
            self.sessions.create(self.socket)

    def test_session_find_by_socket(self):
        """Test that we can find a session by its socket."""
        assert self.sessions.find_by_socket(self.socket) is self.session

    def test_session_active(self):
        """Test that we can determine if a session should be closed."""
        assert self.session.active
        self.session._socket = None
        assert not self.session.active
        self.session._socket = self.socket
        self.session.flags.toggle("close")
        assert not self.session.active
        self.session.flags.toggle("close")
        assert self.session.active

    def test_session_address(self):
        """Test that we can get the host address of the session."""
        assert self.session.address

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
        self.socket._commands.append("test")
        assert self.socket.cmd_ready
        self.session.poll()
        assert not self.socket.cmd_ready
        assert self.socket._output.pop(0) == "You sent: test\n"
        assert self.socket._output.pop(0) == self.prompt
        assert not self.socket._output

    def test_session_poll_no_command(self):
        """Test that sending to a session with no input sends a newline."""
        self.session.send("Hello!")
        self.session.poll()
        assert self.socket._output.pop(0) == "\nHello!\n"
        assert self.socket._output.pop(0) == self.prompt
        assert not self.socket._output

    def test_session_check_idle(self):
        """Test that we can determine if a session is idle."""
        assert not self.session.flags.has_any("idle", "close")
        self.session._check_idle()
        assert not self.session.flags.has_any("idle", "close")
        # They've gone idle.
        self.socket._idle = settings.IDLE_TIME
        self.session._check_idle()
        assert "idle" in self.session.flags
        assert "close" not in self.session.flags
        # They came back.
        self.socket._idle = 0
        self.session._check_idle()
        assert not self.session.flags.has_any("idle", "close")
        assert not self.session._output_queue
        assert self.session.active
        # Now they've been idle for a really long time.
        self.socket._idle = settings.IDLE_TIME_MAX
        self.session._check_idle()
        assert self.session.flags.has("close")
        assert (self.session._output_queue.popleft() ==
                "^RDisconnecting due to inactivity. Goodbye!^~\n")
        assert not self.session.active

    def test_session_manager_poll(self):
        """Test that we can poll a session manager to poll all its sessions."""
        # Create a couple more sessions to test with.
        sessions = [self.session,
                    self.sessions.create(self._FakeSocket(), EchoShell),
                    self.sessions.create(self._FakeSocket(), EchoShell)]
        # Change them around a bit and then poll them all.
        sessions[0]._socket._commands.append("test")
        sessions[1]._socket._commands.append("test")
        self.sessions.poll()
        # The first session was flagged for closing in the previous test,
        # so its input should have been ignored and its flag should have
        # been changed from close to closed.
        assert sessions[0]._socket.cmd_ready
        assert not sessions[0]._socket._output
        assert not sessions[0].active
        assert "closed" in sessions[0].flags
        # The second session should have been parsed and output returned.
        assert not sessions[1]._socket.cmd_ready
        assert sessions[1]._socket._output.pop(0) == "You sent: test\n"
        assert sessions[1]._socket._output.pop(0) == self.prompt
        assert not sessions[1]._socket._output
        assert sessions[1].active
        # And the third session didn't do anything, so should be unchanged.
        assert not sessions[2]._socket.cmd_ready
        assert not sessions[2]._socket._output
        assert sessions[2].active

    def test_session_close(self):
        """Test that we can close a session."""
        assert len(self.sessions._sessions) == 3
        session = self.sessions._sessions[2]
        assert session.active
        session.close("bye cause reasons.")
        assert not session.active
        assert session._output_queue.popleft() == "bye cause reasons.\n"
        assert not session._output_queue

    def test_session_manager_prune(self):
        """Test that we can prune the dead sessions from a session manager."""
        assert len(self.sessions._sessions) == 3
        self.sessions.prune()
        assert len(self.sessions._sessions) == 1
