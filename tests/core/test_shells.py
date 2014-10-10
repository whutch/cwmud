# -*- coding: utf-8 -*-
"""Tests for shell management and client input processing."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

import pytest

from atria.core.shells import AlreadyExists, ShellManager, Shell
from atria.core.utils.funcs import joins


class TestShells:

    """A collection of tests for shell management."""

    shells = None
    shell_class = None
    shell = None

    # noinspection PyDocstring
    class _FakeSession:

        def __init__(self):
            self._output = []

        def send(self, data, *more, sep=" ", end="\n"):
            return self._output.append(joins(data, *more, sep=sep) + end)

    session = _FakeSession()

    def test_shell_manager_create(self):
        """Test that we can create a shell manager.

        This is currently redundant, importing the shells package already
        creates one, but we can keep the it for symmetry and in case
        that isn't always so.

        """
        type(self).shells = ShellManager()
        assert self.shells

    # noinspection PyUnusedLocal
    def test_shell_manager_register(self):

        """Test that we can register a new shell through a shell manager."""

        @self.shells.register
        class TestShell(Shell):

            """A test shell."""

            def init(self):
                """Initialize this test shell."""
                self.session.send("you just inited me!")

        type(self).shell_class = TestShell
        assert "TestShell" in self.shells

    def test_shell_manager_register_already_exists(self):
        """Test that trying to re-register a shell fails."""
        with pytest.raises(AlreadyExists):
            self.shells.register(self.shell_class)

    def test_shell_manager_contains(self):
        """Test that we can see if a shell manager contains a shell."""
        assert "TestShell" in self.shells
        assert not "SomeNonExistentShell" in self.shells

    def test_shell_manager_get_shell(self):
        """Test that we can get a shell from a shell manager."""
        assert self.shells["TestShell"] is self.shell_class
        with pytest.raises(KeyError):
            self.shells["SomeNonExistentShell"].init()

    def test_shell_session_property(self):
        """Test that we can get and set the session property of a shell."""
        # noinspection PyCallingNonCallable
        type(self).shell = self.shell_class()
        self.shell.session = self.session
        assert self.shell.session is self.session

    def test_shell_init(self):
        """Test that we can initialize a shell for its session."""
        self.shell.init()
        assert self.session._output.pop() == "you just inited me!\n"
        assert not self.session._output

    def test_shell_get_prompt(self):
        """Test that we can get the prompt for a session."""
        assert self.shell.get_prompt() == "^y>^~ "

    def test_shell_generate_arguments(self):
        """Test that we can parse arguments from input."""
        assert self.shell.get_arguments("test") == ["test"]
        assert (self.shell.get_arguments('`testing` 1 ``2 "3"') ==
                ["testing", "1", "2", "3"])
        assert (self.shell.get_arguments("hi blah blah blah", max_args=1) ==
                ["hi", "blah blah blah"])
        assert (self.shell.get_arguments("this is 'a test'", max_args=50) ==
                ["this", "is", "a test"])
        assert (self.shell.get_arguments("test test test", max_args=0) ==
                ["test test test"])

    def test_shell_parse(self):
        """Test that we can parse client input."""
        self.shell.parse("test")
        assert self.session._output.pop() == "Huh?\n"
        assert not self.session._output
