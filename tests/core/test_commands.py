# -*- coding: utf-8 -*-
"""Test for command management and processing."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

import pytest

from cwmud.core.commands import AlreadyExists, Command, CommandManager


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

            def __init__(self, session, args):
                super().__init__(session, args)
                self.called = False

            def _action(self):
                self.called = True

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

    def test_command_instance(self):
        """Test that we can create a command instance."""
        # noinspection PyCallingNonCallable
        type(self).command = self.command_class(None, ())
        assert self.command

    def test_command_execute_no_session(self):
        """Test that a command instance without a session won't execute."""
        self.command.execute()
        assert not self.command.called

    def test_command_session_property(self):
        """Test that we can get and set the session property of a command."""
        assert self.command.session is None
        self.command.session = self.session
        assert self.command.session is self.session

    def test_command_execute(self):
        """Test that we can execute a command."""
        self.command.execute()
        assert self.command.called
