# -*- coding: utf-8 -*-
"""Tests for shell management and client input processing."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

import pytest

from cwmud.core.shells import AlreadyExists, Command, Shell, ShellManager
from cwmud.core.utils.funcs import joins


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

    class ATestCommand(Command):

        """A test command."""

        def _action(self):
            raise NotImplementedError

    class AnotherCommand(Command):

        """Another test command."""

        no_parse = True

        def _action(self):
            raise NotImplementedError

    def test_shell_manager_create(self):
        """Test that we can create a shell manager.

        This is currently redundant, importing the shells package already
        creates one, but we can keep it for symmetry and in case that
        isn't always so.

        """
        type(self).shells = ShellManager()
        assert self.shells

    def test_shell_manager_register(self):

        """Test that we can register a new shell through a shell manager."""

        @self.shells.register
        class ATestShell(Shell):

            """A test shell."""

            def init(self):
                """Initialize this test shell."""
                self.session.send("you just inited me!")

        type(self).shell_class = ATestShell
        assert "ATestShell" in self.shells

    def test_shell_manager_register_already_exists(self):
        """Test that trying to re-register a shell fails."""
        with pytest.raises(AlreadyExists):
            self.shells.register(self.shell_class)

    def test_shell_manager_register_not_shell(self):
        """Test that trying to register a non-shell fails."""
        with pytest.raises(TypeError):
            self.shells.register(object())

    def test_shell_manager_contains(self):
        """Test that we can see if a shell manager contains a shell."""
        assert "ATestShell" in self.shells
        assert "SomeNonExistentShell" not in self.shells

    def test_shell_manager_get_shell(self):
        """Test that we can get a shell from a shell manager."""
        assert self.shells["ATestShell"] is self.shell_class
        with pytest.raises(KeyError):
            self.shells["SomeNonExistentShell"].init()

    def test_shell_create(self):
        """Test that we can create a new shell instance."""
        # noinspection PyCallingNonCallable
        type(self).shell = self.shell_class()
        assert self.shell

    def test_shell_init(self):
        """Test that we can initialize a shell for its session."""
        self.shell._set_weak("session", self.session)
        self.shell.init()
        assert self.session._output.pop() == "you just inited me!\n"
        assert not self.session._output

    def test_shell_get_session(self):
        """Test that we can get the session property of a shell."""
        assert self.shell.session is self.session

    def test_shell_set_session_and_init(self):
        """Test that we can set the session property of a shell and init it."""
        assert not self.session._output
        # Setting the session to None should not init the shell.
        self.shell.session = None
        assert not self.session._output
        # And setting it to a session should init the shell.
        self.shell.session = self.session
        assert self.shell.session is self.session
        assert self.session._output.pop() == "you just inited me!\n"
        assert not self.session._output

    def test_shell_get_prompt(self):
        """Test that we can get the prompt for a session."""
        assert self.shell.get_prompt() == "^y>^~ "

    def test_shell_validate_verb(self):
        """Test that we can validate a command verb."""
        self.shell._validate_verb("say")
        with pytest.raises(ValueError):
            self.shell._validate_verb("")
        with pytest.raises(ValueError):
            self.shell._validate_verb(5)
        with pytest.raises(ValueError):
            self.shell._validate_verb("b33p")

    def test_shell_add_verbs(self):
        """Test that we can add verbs to a shell's verb store."""
        assert not self.shell._verbs
        self.shell.add_verbs(self.ATestCommand, "test", "t", "!")
        assert ("test" in self.shell._verbs and
                "t" in self.shell._verbs and
                "!" in self.shell._verbs)

    def test_shell_add_verbs_not_command(self):
        """Test that trying to add verbs for a non-Command fails."""
        with pytest.raises(TypeError):
            self.shell.add_verbs(True, "nope")
        with pytest.raises(TypeError):
            self.shell.add_verbs(Shell, "nope")

    def test_shell_add_verbs_already_exists(self):
        """Test that trying to re-add a verb to a store fails."""
        with pytest.raises(AlreadyExists):
            self.shell.add_verbs(self.ATestCommand, "nope", "test")
        # All of the verbs should have been validated first, so "nope"
        # shouldn't have been added either.
        assert "nope" not in self.shell._verbs

    def test_shell_add_verbs_truncated(self):
        """Test that truncated verbs are added as well."""
        self.shell.add_verbs(self.AnotherCommand, "toot")
        for verb in ("toot", "too", "to"):
            assert self.shell._verbs[verb] is self.AnotherCommand
        # "t" was explicitly registered to TestCommand, so it shouldn't
        # have been overridden by the truncation loop.
        assert self.shell._verbs["t"] is self.ATestCommand

    def test_shell_get_command(self):
        """Test that we can get a command by its verb in the shell."""
        assert self.shell.get_command("test") is self.ATestCommand
        assert self.shell.get_command("!") is self.ATestCommand
        assert not self.shell.get_command("nope")

    def test_shell_find_command(self):
        """Test that we can find a command in the shell's lineage."""
        Shell.add_verbs(self.ATestCommand, "beep")
        assert not self.shell.get_command("beep")
        assert self.shell.find_command("beep") is self.ATestCommand

    def test_shell_remove_verbs(self):
        """Test that we can remove verbs from a shell's verb store."""
        self.shell.remove_verbs("toot")
        for verb in ("toot", "too", "to"):
            assert verb not in self.shell._verbs
        # "t" is registered to TestCommand, and shouldn't have been removed.
        assert "t" in self.shell._verbs
        # Remove everything else.
        self.shell.remove_verbs("test", "!", "nope")
        assert not self.shell._verbs

    def test_shell_one_argument(self):
        """Test that we can break off one argument from some client input."""
        assert (self.shell._one_argument("this is 'a test'") ==
                ("this", " is 'a test'"))
        assert self.shell._one_argument("test") == ("test", "")
        assert self.shell._one_argument("") == ("", "")
        assert self.shell._one_argument("'test") == ("test", "")

    def test_shell_iter_arguments(self):
        """Test that we can iterate all the arguments from some input."""
        args = self.shell._iter_arguments("this is 'a test'")
        assert next(args) == "this"
        assert next(args) == "is"
        assert next(args) == "a test"
        assert (tuple(self.shell._iter_arguments("")) ==
                tuple(self.shell._iter_arguments(" ")) == ())

    def test_shell_get_arguments(self):
        """Test that we can parse arguments from input."""
        assert self.shell._get_arguments(" '' ") == []
        assert self.shell._get_arguments("test") == ["test"]
        assert (self.shell._get_arguments('`testing` 1 ``2 "3"') ==
                ["testing", "1", "2", "3"])
        assert (self.shell._get_arguments("hi blah blah blah", max_args=1) ==
                ["hi", " blah blah blah"])
        assert (self.shell._get_arguments("this is 'a test'", max_args=50) ==
                ["this", "is", "a test"])
        assert (self.shell._get_arguments("test test test", max_args=0) ==
                ["test test test"])

    def test_shell_parse(self):
        """Test that we can parse client input."""
        self.shell.parse("test")
        # There are no commands registered yet.
        assert self.session._output.pop() == "Huh?\n"
        self.shell.parse("")
        assert not self.session._output
        self.shell.parse(" ")
        assert self.session._output.pop() == "Huh?\n"
        # Re-register the command so we know it can be executed.
        self.shell.add_verbs(self.ATestCommand, "test")
        self.shell.add_verbs(self.AnotherCommand, "!")
        with pytest.raises(NotImplementedError):
            self.shell.parse("test")
        with pytest.raises(NotImplementedError):
            self.shell.parse("!bloop")
