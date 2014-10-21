# -*- coding: utf-8 -*-
"""Tests for event handling."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

import pytest

from atria.core.events import EventManager


class TestHooking:

    """A collection of tests for event hooking."""

    events = None
    event = None
    array = []

    @staticmethod
    def _dummy_func():
        pass

    def test_create_event_manager(self):
        """Test that we can create a new event manager.

        This is currently redundant, importing the events package already
        creates one, but we can keep it for symmetry and in case that
        isn't always so.

        """
        type(self).events = EventManager()
        assert self.events

    def test_create_event(self):
        """Test that we can create a new event."""
        type(self).event = self.events.get_or_make("test")
        assert self.event

    def test_get_event(self):
        """Test that we can get an already made event."""
        assert self.events.get_or_make("test") is self.event

    def test_pre_hook(self):
        """Test pre-hooking through a decorator."""
        @self.events.hook("test", pre=True)
        def _dummy_func():
            pass
        assert (_dummy_func, True) in self.event.hooks

    def test_post_hook(self):
        """Test hooking with a callback."""
        self.events.hook("test", callback=self._dummy_func)
        assert (self._dummy_func, False) in self.event.hooks

    def test_unhook_bad_event_name(self):
        """Test unhooking a non-existent event."""
        events = self.events._events
        self.events.unhook("yeah")
        assert self.events._events == events
        assert self.event.hooks

    def test_unhook(self):
        """Test unhooking by callback."""
        assert self.event.hooks
        for cb, pre in self.event.hooks:
            self.events.unhook("test", callback=cb)
            assert (cb, pre) not in self.event.hooks

    def test_unhook_duplicate_func(self):
        """Test unhooking by callback with multiple matching functions."""
        self.events.hook("test", callback=self._dummy_func, pre=True)
        self.events.hook("test", callback=self._dummy_func)
        assert self.event.hooks == [(self._dummy_func, True),
                                    (self._dummy_func, False)]
        self.events.unhook("test", callback=self._dummy_func)
        assert not self.event.hooks

    def test_hook_namespace(self):
        """Test hooking with a namespace."""
        self.events.hook("test", "test_namespace",
                         callback=self._dummy_func)
        assert "test_namespace" in self.event.named_hooks
        namespace = self.event.named_hooks["test_namespace"]
        assert self._dummy_func in namespace

    def test_unhook_namespace(self):
        """Test unhooking by namespace."""
        self.events.unhook("test", "test_namespace")
        assert "test_namespace" not in self.event.named_hooks
        assert (self._dummy_func, False) not in self.event.hooks

    def test_unhook_namespace_and_callback(self):
        """Test unhooking by both namespace and callback."""
        other_callback = lambda: None
        self.events.hook("test", "test_namespace", callback=self._dummy_func)
        self.events.hook("test", "test_namespace", callback=other_callback)
        assert (self._dummy_func, False) in self.event.hooks
        assert (other_callback, False) in self.event.hooks
        assert "test_namespace" in self.event.named_hooks
        self.events.unhook("test", "test_namespace", callback=self._dummy_func)
        assert self.event.hooks == [(other_callback, False)]
        assert "test_namespace" in self.event.named_hooks
        self.events.unhook("test", "test_namespace", callback=other_callback)
        assert not self.event.hooks
        assert not self.event.named_hooks

    def test_unhook_namespace_by_callback_only(self):
        """Test unhooking by callback where namespace points to callback.

        We want to ensure that if we are unhooking by callback, that any
        entries in named_hooks that point to that callback are cleaned up too.

        """
        self.events.hook("test", "test_namespace", callback=self._dummy_func)
        assert (self._dummy_func, False) in self.event.hooks
        assert "test_namespace" in self.event.named_hooks
        self.events.unhook("test", callback=self._dummy_func)
        assert not self.event.hooks
        assert not self.event.named_hooks

    def test_unhook_partial_wildcard(self):
        """Test partial wildcard unhooking."""
        events = []
        for name in ["not_me", "test1", "test2"]:
            self.events.hook(name, "test_namespace",
                             callback=self._dummy_func)
            event = self.events.get_or_make(name)
            assert (self._dummy_func, False) in event.hooks
            assert "test_namespace" in event.named_hooks
            events.append(event)
        self.events.unhook("test*", "test_namespace")
        assert (self._dummy_func, False) in events[0].hooks
        assert "test_namespace" in events[0].named_hooks
        for event in events[1:]:
            assert not event.hooks
            assert not event.named_hooks

    def test_unhook_wildcard(self):
        """Test full wildcard unhooking."""
        events = []
        for name in ["test1", "test_2", "testTEST"]:
            self.events.hook(name, "test_namespace",
                             callback=self._dummy_func)
            event = self.events.get_or_make(name)
            assert (self._dummy_func, False) in event.hooks
            assert "test_namespace" in event.named_hooks
            events.append(event)
        self.events.unhook("*", "test_namespace")
        for event in events:
            assert not event.hooks
            assert not event.named_hooks

    def test_unhook_everything(self):

        """Test unhooking everything from event."""

        @self.events.hook("test", "some_namespace", pre=True)
        def _dummy_func1():
            pass
        assert (_dummy_func1, True) in self.event.hooks
        assert "some_namespace" in self.event.named_hooks

        @self.events.hook("test", "some_other_namespace")
        def _dummy_func2():
            pass
        assert (_dummy_func2, False) in self.event.hooks
        assert "some_other_namespace" in self.event.named_hooks

        _dummy_func3 = lambda: None
        self.events.hook("test", callback=_dummy_func3)
        assert (_dummy_func3, False) in self.event.hooks

        self.events.unhook("test")
        assert not self.event.hooks
        assert not self.event.named_hooks

    def test_event_fire(self):
        """Test firing an event."""
        self.events.hook("test", callback=lambda: self.array.append(1),
                         pre=True)
        self.events.hook("test", callback=lambda: self.array.append(3))
        with self.events.fire("test"):
            self.array.append(2)
        assert self.array == [1, 2, 3]

    def test_event_fire_now(self):
        """Test firing an event with the `now` method."""
        self.events.fire("test").now()
        assert self.array == [1, 2, 3, 1, 3]

    def test_event_fire_exception(self):
        """Test that exceptions from an event firing are re-raised."""
        with pytest.raises(SyntaxError):
            with self.events.fire("test"):
                raise SyntaxError()
