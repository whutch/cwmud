# -*- coding: utf-8 -*-
"""Tests for event handling."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

import pytest

from cwmud.core.events import EventManager


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
        assert len(self.event.hooks) == 1
        assert self.event.hooks[-1].callback is _dummy_func
        assert self.event.hooks[-1].pre is True

    def test_post_hook(self):
        """Test hooking with a callback."""
        self.events.hook("test", callback=self._dummy_func)
        assert len(self.event.hooks) == 2
        assert self.event.hooks[-1].callback is self._dummy_func
        assert self.event.hooks[-1].pre is False

    def test_unhook_bad_event_name(self):
        """Test unhooking a non-existent event."""
        events = self.events._events
        self.events.unhook("yeah")
        assert self.events._events == events
        assert self.event.hooks

    def test_unhook(self):
        """Test unhooking by callback."""
        assert len(self.event.hooks) == 2
        for hook in self.event.hooks[:]:
            self.events.unhook("test", callback=hook.callback)
        assert not self.event.hooks

    def test_unhook_duplicate_func(self):
        """Test unhooking by callback with multiple matching hooks."""
        self.events.hook("test", callback=self._dummy_func, pre=True)
        self.events.hook("test", callback=self._dummy_func)
        assert len(self.event.hooks) == 2
        self.events.unhook("test", callback=self._dummy_func)
        assert not self.event.hooks

    def test_hook_namespace(self):
        """Test hooking with a namespace."""
        self.events.hook("test", "test_namespace",
                         callback=self._dummy_func)
        assert len(self.event.hooks) == 1
        assert self.event.hooks[-1].namespace == "test_namespace"
        assert self.event.hooks[-1].callback is self._dummy_func

    def test_unhook_namespace(self):
        """Test unhooking by namespace."""
        assert self.event.hooks
        self.events.unhook("test", "test_namespace")
        assert not self.event.hooks

    def test_unhook_namespace_and_callback(self):
        """Test unhooking by both namespace and callback."""
        other_callback = lambda: None
        self.events.hook("test", "test_namespace", callback=self._dummy_func)
        self.events.hook("test", "test_namespace", callback=other_callback)
        assert len(self.event.hooks) == 2
        self.events.unhook("test", "test_namespace", callback=self._dummy_func)
        assert len(self.event.hooks) == 1
        assert self.event.hooks[-1].namespace == "test_namespace"
        assert self.event.hooks[-1].callback is other_callback
        self.events.unhook("test", "test_namespace", callback=other_callback)
        assert not self.event.hooks

    def test_unhook_namespace_by_callback_only(self):
        """Test unhooking by callback where namespace points to callback.

        We want to ensure that if we are unhooking by callback, that any
        entries in named_hooks that point to that callback are cleaned up too.

        """
        self.events.hook("test", "test_namespace", callback=self._dummy_func)
        assert len(self.event.hooks) == 1
        assert self.event.hooks[-1].namespace == "test_namespace"
        assert self.event.hooks[-1].callback is self._dummy_func
        self.events.unhook("test", callback=self._dummy_func)
        assert not self.event.hooks

    def test_unhook_partial_wildcard(self):
        """Test partial wildcard unhooking."""
        events = []
        for name in ["not_me", "test1", "test2"]:
            self.events.hook(name, "test_namespace",
                             callback=self._dummy_func)
            event = self.events.get_or_make(name)
            assert len(event.hooks) == 1
            assert event.hooks[-1].namespace == "test_namespace"
            assert event.hooks[-1].callback is self._dummy_func
            events.append(event)
        self.events.unhook("test*", "test_namespace")
        assert len(events[0].hooks) == 1
        assert events[0].hooks[-1].namespace == "test_namespace"
        assert events[0].hooks[-1].callback is self._dummy_func
        for event in events[1:]:
            assert not event.hooks

    def test_unhook_wildcard(self):
        """Test full wildcard unhooking."""
        events = []
        for name in ["test1", "test_2", "testTEST"]:
            self.events.hook(name, "test_namespace",
                             callback=self._dummy_func)
            event = self.events.get_or_make(name)
            assert len(event.hooks) == 1
            assert event.hooks[-1].namespace == "test_namespace"
            assert event.hooks[-1].callback is self._dummy_func
            events.append(event)
        self.events.unhook("*", "test_namespace")
        for event in events:
            assert not event.hooks

    def test_unhook_everything(self):

        """Test unhooking everything from event."""

        @self.events.hook("test", "some_namespace", pre=True)
        def _dummy_func1():
            pass

        @self.events.hook("test", "some_other_namespace")
        def _dummy_func2():
            pass

        _dummy_func3 = lambda: None
        self.events.hook("test", callback=_dummy_func3)

        assert len(self.event.hooks) == 3
        assert self.event.hooks[0].namespace == "some_namespace"
        assert self.event.hooks[0].callback is _dummy_func1
        assert self.event.hooks[1].namespace == "some_other_namespace"
        assert self.event.hooks[1].callback is _dummy_func2
        assert self.event.hooks[2].namespace is None
        assert self.event.hooks[2].callback is _dummy_func3
        self.events.unhook("test")
        assert not self.event.hooks

    def test_hook_after(self):
        """Test hooking a callback after another namespace."""
        self.events.hook("test", "test1", callback=self._dummy_func,
                         after="test3")
        assert len(self.event.hooks) == 1
        self.events.hook("test", "test2", callback=self._dummy_func,
                         after="test4")
        assert len(self.event.hooks) == 2
        assert self.event.hooks[0].namespace == "test1"
        assert self.event.hooks[1].namespace == "test2"
        self.events.hook("test", "test3", callback=self._dummy_func,
                         after="test4")
        assert len(self.event.hooks) == 3
        assert self.event.hooks[0].namespace == "test2"
        assert self.event.hooks[1].namespace == "test3"
        assert self.event.hooks[2].namespace == "test1"
        self.events.hook("test", "test4", callback=self._dummy_func)
        assert len(self.event.hooks) == 4
        assert self.event.hooks[0].namespace == "test4"
        assert self.event.hooks[1].namespace == "test2"
        assert self.event.hooks[2].namespace == "test3"
        assert self.event.hooks[3].namespace == "test1"

    def test_hook_after_circular_references(self):
        """Test hooks with circular `after` references will fail."""
        self.events.hook("test", "test1", callback=self._dummy_func,
                         after="test2")
        with pytest.raises(OverflowError):
            self.events.hook("test", "test2", callback=self._dummy_func,
                             after="test1")

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
