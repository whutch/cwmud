# -*- coding: utf-8 -*-
"""Test for command management and processing."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

import pytest

from atria.core.commands import AlreadyExists, CommandManager, Command


class TestCommands:

    """A collection of tests for command management."""

    commands = None
    command_class = None
    command = None

    class _FakeSession:
        pass

    session = _FakeSession()

    def test_command_manager_create(self):
        """Test that we can create a command manager.

        This is currently redundant, importing the commands package already
        creates one, but we can keep it for symmetry and in case that
        isn't always so.

        """
        type(self).commands = CommandManager()
        assert self.commands

    def test_command_manager_get_name(self):
        """Test that we can figure out the name for an argument."""
        assert self.commands._get_name(Command) == "Command"
        assert self.commands._get_name("TestCommand") == "TestCommand"

    def test_command_manager_register(self):

        """Test that we can register new commands through a command manager."""

        @self.commands.register
        class TestCommand(Command):

            """A test command."""

            pass

        type(self).command_class = TestCommand
        assert "TestCommand" in self.commands

    def test_command_manager_register_by_argument(self):
        """Test that we can register a new command by argument."""
        self.commands.register(command=Command)
        assert "Command" in self.commands

    def test_command_manager_register_not_command(self):
        """Test that trying to register a non-command fails."""
        with pytest.raises(TypeError):
            self.commands.register(command=object())

    def test_command_manager_register_already_exists(self):
        """Test that trying to register an existing command name fails."""
        with pytest.raises(AlreadyExists):
            self.commands.register(command=self.command_class)

    def test_command_manager_contains(self):
        """Test that we can see if a command manager contains a command."""
        assert "TestCommand" in self.commands
        assert Command in self.commands
        assert "some_nonexistent_command" not in self.commands
        assert CommandManager not in self.commands

    def test_command_manager_get_command(self):
        """Test that we can get a command from a command manager."""
        assert self.commands["TestCommand"] is self.command_class
        with pytest.raises(KeyError):
            self.commands["some_nonexistent_command"].process()

    def test_command_session_property(self):
        """Test that we can get and set the session property of a command."""
        # noinspection PyCallingNonCallable
        type(self).command = self.command_class(None, ())
        assert self.command.session is None
        self.command.session = self.session
        assert self.command.session is self.session