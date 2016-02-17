# -*- coding: utf-8 -*-
"""Scheduling and timer management."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from collections import OrderedDict
import re
from time import sleep, time as now

from .events import EVENTS
from .logs import get_logger
from .utils.exceptions import AlreadyExists
from .utils.funcs import is_hashable


log = get_logger("time")


# Code readability
SECS_PER_HOUR = 60 * 60
SECS_PER_DAY = 24 * SECS_PER_HOUR

# Timing
PULSE_PER_SECOND = 25
_PULSE_TIME = 1.0 / PULSE_PER_SECOND
# Increasing the pulses per second will increase the server responsiveness
# as there will be less potential lag time between IO queueing and the
# server processing it, but the increased number of loops and the processing
# overhead can greatly impact performance.  Be especially mindful if you have
# hooks to events that fire each pulse loop ("server_loop", "time_pulse", etc).

SECS_PER_TICK = 60


_match_secs = re.compile(r"(\d+)\s*s(?:ec(?:ond)?(?:s)?)?$")
_match_mins = re.compile(r"(\d+)\s*m(?:in(?:ute)?(?:s)?)?$")
_match_pulses = re.compile(r"(\d+)\s*(?:p(?:ulse(?:s)?)?)?$")


def duration_to_pulses(duration):
    """Convert an amount of time into pulses.

    Accepts `duration` in pulses, seconds, or minutes, in a range of
    abbreviated forms.  An unspecified measurement of time will be
    converted into pulses.

    :param str|int duration: The amount of time to convert
    :returns int: The converted amount of pulses
    :raises ValueError: if duration could not be parsed

    """
    if isinstance(duration, int):
        return duration
    if duration.isdigit():
        return int(duration)
    duration = duration.lower()
    if duration == "now":
        return 1
    match = _match_secs.match(duration)
    if match:
        return int(match.groups()[0]) * PULSE_PER_SECOND
    match = _match_mins.match(duration)
    if match:
        return int(match.groups()[0]) * PULSE_PER_SECOND * 60
    match = _match_pulses.match(duration)
    if match:
        return int(match.groups()[0])
    raise ValueError("invalid duration")


class TimerManager:

    """A manager for timer creation and handling."""

    def __init__(self):
        """Create a new timer manager."""
        self._time = now()
        self._start_time = self._time
        self._next_pulse = self._time + _PULSE_TIME
        self._timers = OrderedDict()

    @property
    def time(self):
        """Return when the last poll was, in seconds since the epoch."""
        return self._time

    @property
    def started(self):
        """Return when this manager started, in seconds since the epoch."""
        return self._start_time

    @property
    def uptime(self):
        """Return how long since this started, in seconds since the epoch."""
        return self._time - self._start_time

    def __contains__(self, timer):
        return timer in self._timers

    def __getitem__(self, timer):
        return self._timers[timer]

    def _update_time(self):
        """Update the current time.

        This is the only place that self._time should be changed.

        """
        self._time = now()

    def create(self, duration, name=None, repeat=0, save=True, callback=None):
        """Create a timer that will call a function every so often.

        If you do not provide `callback`, this will instead return a
        decorator that will use the decorated function as the callback.

        Note: It is not a timer's job to know what systems, scripts, objects,
        etc are associated with it; anything that creates timers should also
        destroy them when they are unloaded, disabled, destroyed, etc.

        :param str|int duration: The amount of time between repetitions
        :param hashable name: Optional, a key for the timer
        :param int repeat: Optional, number of times to repeat (or -1
                           to repeat until killed)
        :param bool save: Whether this timer should be saved between reboots
        :param function callback: Optional, a callback for the timer
        :returns Timer|function: A timer instance if a callback was provided,
                                  otherwise a decorator to create the timer
        :raises AlreadyExists: If `name` is provided and that name
                               already exists
        :raises KeyError: If `name` is provided and is not hashable
        :raises TypeError: If `callback` or decorated object is not callable
        :raises ValueError: If `duration` is invalid or zero

        """
        def _inner(func):
            if not callable(func):
                raise TypeError("callback is not callable", (func,))
            if name is not None:
                if not is_hashable(name):
                    raise KeyError("invalid name; must be hashable")
                if name in self._timers:
                    raise AlreadyExists(name, self._timers[name], func)
            pulses = duration_to_pulses(duration)
            if not pulses:
                raise ValueError("duration cannot be zero")
            timer = Timer(self, pulses, name, repeat, save, func)
            self._timers[name if name is not None else timer] = timer
            return timer
        if callback is not None:
            return _inner(callback)
        else:
            return _inner

    def kill(self, timer):
        """Destroy a timer if it exists, by name or reference.

        :param str|Timer timer: The timer to kill
        :returns None:

        """
        if timer in self._timers:
            timer = self._timers.pop(timer)
        if isinstance(timer, Timer) and timer.live:
            # Timer.kill and this call each other, so we need to be
            # mindful of an infinite loop.
            timer.kill()

    def pulse(self):
        """Pulse each timer once."""
        for timer in self._timers.values():
            timer.pulse()

    def sleep_excess(self, pulses=1):
        """Sleep away the excess time of a number of pulses.

        :param int pulses: The number of pulses to sleep through
        :returns None:

        """
        for n in range(pulses):
            self._update_time()
            if self._time < self._next_pulse:
                sleep(self._next_pulse - self._time)
                self._update_time()
            with EVENTS.fire("time_pulse", self._time):
                self._next_pulse += _PULSE_TIME


class Timer:

    """A timer that calls a function every so often.

    Individual timers don't actually know or care what time is it, they only
    count how many times they've been pulsed and react accordingly.

    """

    def __init__(self, manager, pulses, name, repeat, save, callback):
        """Create a new timer.

        Don't do this yourself, call TimerManager.create instead.

        """
        self._manager = manager
        # History
        self._started = manager.started
        self._total_pulses = 0
        # Settings
        self._name = name
        self.pulses = pulses
        self.repeat = repeat
        self.save = save
        self.callback = callback
        # State
        self._count = 0
        self._live = True

    def __call__(self, *args, **kwargs):
        # This is likely because you used TimerManager.create as
        # a decorator but still passed a callback= argument.
        raise SyntaxError("tried to call a timer, "
                          "did you use it as a decorator?")

    @property
    def key(self):
        """Return the key used to store this timer."""
        return self._name if self._name is not None else self

    @property
    def count(self):
        """Return the current pulse count for this timer."""
        return self._count

    @property
    def live(self):
        """Return whether this timer is alive or not."""
        return self._live

    def pulse(self):
        """Pulse this timer.

        Don't do this yourself, call TimerManager.poll instead.

        """
        if not self._live:
            return
        self._total_pulses += 1
        self._count += 1
        if self._count < self.pulses:
            return
        # Time's up.
        self.callback()
        if self.repeat != 0:
            # Either there are still repetitions to go (1+)
            # or it loops until killed (-1).
            self._count = 0
            if self.repeat > 0:
                self.repeat -= 1
        else:
            self.kill()

    def kill(self):
        """Kill this timer.  Just murder it dead."""
        self._live = False
        if self.key in self._manager:
            self._manager.kill(self.key)


# We create a global TimerManager here for convenience, and while the server
# will generally only need one to work with, they are NOT singletons and you
# can make more TimerManager instances if you like.
TIMERS = TimerManager()
