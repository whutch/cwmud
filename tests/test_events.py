# -*- coding: utf-8 -*-
"""Tests for event handling"""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from atria.core.events import EventManager


def test_create_event_manager():
    """Test that we can create an event manager."""
    events = EventManager()
    assert events


def test_create_event():
    """Test that we can create an event."""
    events = EventManager()
    event = events.get_or_make("test")
    assert event


class TestHooking:

    """Tests for event hooking."""

    events = EventManager()
    event = events.get_or_make("test")

    @staticmethod
    def _dummy_func():
        pass

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

    def test_unhook_namespace_by_callback(self):
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


def test_fire_event():
    """Test firing an event."""
    events = EventManager()
    array = []
    events.hook("test", callback=lambda: array.append(1), pre=True)
    events.hook("test", callback=lambda: array.append(3))
    with events.fire("test"):
        array.append(2)
    assert array == [1, 2, 3]
