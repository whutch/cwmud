# -*- coding: utf-8 -*-
"""Tests for text menus."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

import pytest

from cwmud.core.menus import AlreadyExists, Menu, MenuManager
from cwmud.core.utils.funcs import joins


class TestMenus:

    """A collection of tests for text menus."""

    menus = None
    menu_class = None
    menu = None

    # noinspection PyDocstring
    class _FakeSession:

        def __init__(self):
            self._output = []

        def send(self, data, *more, sep=" ", end="\n"):
            return self._output.append(joins(data, *more, sep=sep) + end)

    session = _FakeSession()

    def test_menu_manager_create(self):
        """Test that we can create a menu manager.

        This is currently redundant, importing the menus package already
        creates one, but we can keep it for symmetry and in case that
        isn't always so.

        """
        type(self).menus = MenuManager()
        assert self.menus

    def test_menu_manager_register(self):

        """Test that we can register a new menu through a manager."""

        @self.menus.register
        class TestMenu(Menu):
            """A test menu."""

        type(self).menu_class = TestMenu
        assert "TestMenu" in self.menus._menus

    def test_menu_manager_register_already_exists(self):
        """Test that trying to re-register a menu fails."""
        with pytest.raises(AlreadyExists):
            self.menus.register(self.menu_class)

    def test_menu_manager_register_not_menu(self):
        """Test that trying to register a non-menu fails."""
        with pytest.raises(TypeError):
            self.menus.register(object())

    def test_menu_manager_contains(self):
        """Test that we can see if a menu manager contains a menu."""
        assert "TestMenu" in self.menus
        assert "SomeNonExistentMenu" not in self.menus

    def test_menu_manager_get_menu(self):
        """Test that we can get a menu from a menu manager."""
        assert self.menus["TestMenu"] is self.menu_class
        with pytest.raises(KeyError):
            self.menus["SomeNonExistentMenu"].resolve("yeah")

    def test_menu_create(self):
        """Test that we can create a new menu instance."""
        # noinspection PyCallingNonCallable
        type(self).menu = self.menu_class(self.session)
        assert self.menu
