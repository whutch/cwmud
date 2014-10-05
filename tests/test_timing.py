# -*- coding: utf-8 -*-
"""Tests for scheduling and timer management."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

import pytest

from atria.core.timing import (_PULSE_TIME, PULSE_PER_SECOND, AlreadyExists,
                               duration_to_pulses, TimerManager)


dtp = duration_to_pulses  # For brevity


def test_seconds_to_pulses():
    """Test converting seconds to pulses."""
    assert (dtp("5s") == dtp("5sec") == dtp("5secs") ==
            dtp("5 s") == dtp("5 sec") == dtp("5 secs") ==
            dtp("5second") == dtp("5seconds") ==
            dtp("5 second") == dtp("5 seconds") ==
            5 * PULSE_PER_SECOND)


def test_minutes_to_pulses():
    """Test converting minutes to pulses."""
    assert (dtp("5m") == dtp("5min") == dtp("5mins") ==
            dtp("5 m") == dtp("5 min") == dtp("5 mins") ==
            dtp("5minute") == dtp("5minutes") ==
            dtp("5 minute") == dtp("5 minutes") ==
            5 * PULSE_PER_SECOND * 60)


def test_pulses_to_pulses():
    """Test converting pulses to.. pulses?"""
    assert (dtp(5) == dtp("5") ==
            dtp("5p") == dtp("5pulse") == dtp("5pulses") ==
            dtp("5 p") == dtp("5 pulse") == dtp("5 pulses") == 5)


def test_create_timer_manager():
    """Test that we can create a timer manager.

    This is currently redundant, importing the timing package already creates
    one, but we can keep it for symmetry and in case that isn't always so.

    """
    timers = TimerManager()
    assert timers


class TestTimerManager:

    """A collection of tests for timer managers and their timers."""

    timers = TimerManager()
    _timer = []
    called = []

    @property
    def timer(self):
        """A shortcut to get to our timer between tests."""
        return self._timer[0] if self._timer else None

    def test_timer_manager_properties(self):
        """Test that the properties on a timer manager return something."""
        assert self.timers.time
        assert self.timers.started
        assert self.timers.uptime

    def test_create_timer_unnamed(self):
        """Test that we can create an unnamed timer."""
        timer = self.timers.create(1, callback=lambda: None)
        assert timer
        self._timer.append(timer)

    def test_create_timer_named(self):
        """Test that we can create a named timer."""
        timer = self.timers.create(1, "test", callback=lambda: None)
        assert timer

    def test_create_timer_duplicate_name(self):
        """Test that creating a named timer with an existing name fails."""
        with pytest.raises(AlreadyExists):
            self.timers.create(1, "test", callback=lambda: None)

    def test_create_timer_bad_name(self):
        """Test that creating a timer with an un-hashable name fails."""
        with pytest.raises(KeyError):
            self.timers.create(1, [], callback=lambda: None)

    def test_create_timer_bad_callback(self):
        """Test that creating a timer with a non-callable callback fails."""
        with pytest.raises(TypeError):
            self.timers.create(1, callback="not a callback")

    def test_create_timer_bad_duration(self):
        """Test that creating a timer with a bad duration fails."""
        with pytest.raises(ValueError):
            self.timers.create(0, callback=lambda: None)
        with pytest.raises(ValueError):
            self.timers.create("eleventy jillion!", callback=lambda: None)

    def test_timer_manager_contains(self):
        """Test that we can check if a timer is in a timer manager."""
        # By reference
        assert self.timer in self.timers
        assert None not in self.timers
        # And by name
        assert "test" in self.timers
        assert "a non-existent timer" not in self.timers

    def test_timer_manager_getitem(self):
        """Test that we can get a timer from a timer manager."""
        # By reference
        assert self.timers[self.timer] is self.timer
        # And by name
        assert self.timers["test"]
        timer = self.timers.create(2, "test2", repeat=2, callback=lambda: None)
        assert self.timers["test2"] is timer
        with pytest.raises(KeyError):
            assert self.timers["a non-existent timer"]

    def test_timer_properties(self):
        """Test that the properties on a timer return something."""
        assert self.timer.live is True or self.timer.live is False
        assert self.timer.key is self.timer
        assert self.timers["test"].key is "test"
        assert self.timer.count == 0

    def test_timer_pulse(self):
        """Test that pulsing a timer correctly updates it."""
        timer = self.timers["test2"]
        timer.callback = lambda: self.called.append(self.timers.time)
        assert timer.pulses == 2
        assert timer.count == 0 and timer.repeat == 2
        timer.pulse()
        assert timer.count == 1 and timer.repeat == 2
        assert self.called == []
        timer.pulse()
        assert timer.count == 0 and timer.repeat == 1
        assert self.called and self.called[-1] == self.timers.time

    def test_timer_kill_from_manager(self):
        """Test that we can kill a timer from its manager."""
        self.timers.kill(self.timer)
        assert not self.timer.live
        assert self.timer not in self.timers

    def test_timer_kill_from_timer(self):
        """Test that we can kill a timer from itself."""
        timer = self.timers["test"]
        timer.kill()
        assert not timer.live
        assert "test" not in self.timers

    def test_dead_timer_wont_pulse(self):
        """Test that a dead timer won't pulse anymore."""
        self.timer.callback = lambda: self.called.append("oops")
        assert not self.timer.live
        assert self.timer not in self.timers
        assert self.timer.count == 0 and self.timer.repeat == 0
        self.timer.pulse()
        assert self.called[-1] != "oops"
        assert self.timer.count == 0 and self.timer.repeat == 0

    def test_timer_manager_poll(self):
        """Test polling a timer manager."""
        timer = self.timers["test2"]
        assert timer.count == 0 and timer.repeat == 1
        next_pulse = self.timers._next_pulse
        # Poll once, ensuring that we get the next pulse.
        self.timers.poll(wait=True)
        # Our timer should have counted and the next pulse updated.
        next_pulse += _PULSE_TIME
        assert next_pulse == self.timers._next_pulse
        assert timer.count == 1 and timer.repeat == 1
        # Poll again but don't wait for next pulse.
        self.timers._next_pulse += 1000  # Bump up the next pulse to ensure we
        # don't accidentally hit it anyway without waiting (likely since all
        # these tests have taken way longer than a single pulse time).
        self.timers.poll()
        self.timers._next_pulse -= 1000  # Bring it back down.
        # Nothing should have changed.
        assert next_pulse == self.timers._next_pulse
        assert timer.count == 1 and timer.repeat == 1
        # Do it again, and wait this time.
        self.timers.poll(wait=True)
        # Our timer should have rolled over and the next pulse updated.
        next_pulse += _PULSE_TIME
        assert next_pulse == self.timers._next_pulse
        assert timer.count == 0 and timer.repeat == 0
        assert self.called and self.called[-1] == self.timers.time

    def test_timer_pulse_kill(self):
        """Test that a timer dies when it runs its course."""
        timer = self.timers["test2"]
        assert timer.count == 0 and timer.repeat == 0
        self.timers.poll(wait=True)
        assert timer.count == 1 and timer.repeat == 0  # Almost there!
        # Alas, this is the final poll for our brave little timer.
        self.timers.poll(wait=True)
        assert timer.count == 2 and timer.repeat == 0
        assert self.called and self.called[-1] == self.timers.time
        assert not timer.live
        assert not timer.key in self.timers

    def test_timer_repeat_forever(self):
        """Test that a timer can repeat forever."""
        timer = self.timers.create(1, repeat=-1, callback=
                                   lambda: self.called.append(1))
        assert timer.live
        assert timer.count == 0 and timer.repeat == -1
        was_called = len(self.called)
        for n in range(1, 10):
            timer.pulse()
            assert timer.live
            assert timer.count == 0 and timer.repeat == -1
            assert len(self.called) == was_called + n
        timer.kill()
        assert not timer.live
        assert not timer.key in self.timers
