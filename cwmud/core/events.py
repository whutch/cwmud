# -*- coding: utf-8 -*-
"""Event handling."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from .logs import get_logger


log = get_logger("events")


class EventManager:

    """A manager for event registration and handling.

    Events are lazily created; when you call ``hook`` or ``fire``, if the
    target event doesn't already exist, it is implicitly created for you.
    This allows code that hooks an event to be called before the code that
    would have explicitly created it (typically, the module that fires them),
    preventing a lot of circular import headaches.

    """

    def __init__(self):
        """Create a new event manager."""
        self._events = {}

    def get_or_make(self, event_name):
        """Fetch an event, implicitly creating it if necessary.

        :param str event_name: The name of the event to get or create
        :returns Event: The existing or newly created event

        """
        event = self._events.get(event_name)
        if not event:
            event = Event(event_name)
            self._events[event_name] = event
        return event

    def hook(self, event_name, namespace=None, callback=None,
             pre=False, after=None):
        """Hook a callback to an event, optionally through a decorator.

        If an event with the name `event_name` does not exist it will be
        implicitly created for you.

        If you do not provide `callback`, this will instead return a
        decorator that will use the decorated function as the callback.

        :param str event_name: The name of the event to hook
        :param str namespace: Optional, a namespace for the hook
        :param function callback: Optional, a callback for the hook
        :param bool pre: Optional, whether to pre- or post-hook the event
        :param str after: Optional, a namespace that this hook will be inserted
                          after in the hook order
        :returns function|None: A decorator to register an event hook callback
                                or None if callback was provided

        """
        def _inner(func):
            event = self.get_or_make(event_name)
            new_hook = EventHook(func, namespace, pre, after)
            event.hooks.append(new_hook)
            if namespace is not None:
                # Check for existing hooks that should be called after this.
                moved = [new_hook]

                def _check_afters(check_hooks):
                    nonlocal moved
                    move = []
                    for hook in event.hooks:
                        for check_hook in check_hooks:
                            if (hook.after is not None and
                                    hook.after == check_hook.namespace):
                                move.append(hook)
                    if move:
                        for hook in move:
                            if hook in moved:
                                raise OverflowError(
                                    "circular `after` attribute on"
                                    " hook: {}".format(hook.after))
                            event.hooks.remove(hook)
                            event.hooks.append(hook)
                            moved.append(hook)
                        _check_afters(move)

                _check_afters([new_hook])
            return func

        if callback:
            _inner(callback)
        else:
            return _inner

    def unhook(self, event_name, namespace=None, callback=None):
        """Unhook callbacks from an event.

        If an event with the name `event_name` or a wildcard matching it
        does not exist, nothing happens.

        If neither `namespace` nor `callback` are provided, all hooks
        will be stripped from the matching event(s).  Use cautiously.

        :param str event_name: The name of the event to unhook; it can either
                               be an exact match, "name*" for a following
                               wildcard, or "*" for a total wildcard
        :param str namespace: Optional, a namespace to filter by
        :param function callback: Optional, a function to filter by
        :returns None:

        """
        if event_name == "*":
            events = self._events.values()
        elif event_name.endswith("*"):
            events = [event for name, event in self._events.items()
                      if name.startswith(event_name[:-1])]
        else:
            if event_name in self._events:
                events = [self._events.get(event_name)]
            else:
                events = []
        for event in events:
            if callback and namespace is None:
                # Unhook by callback only.
                event.hooks = [hook for hook in event.hooks
                               if hook.callback is not callback]
            elif namespace is not None:
                # Unhook by namespace, with or without a callback.
                if callback:
                    event.hooks = [hook for hook in event.hooks
                                   if hook.namespace != namespace or
                                   hook.callback is not callback]
                else:
                    event.hooks = [hook for hook in event.hooks
                                   if hook.namespace != namespace]
            else:
                # Just unhook everything (not recommended).
                event.hooks = []

    def fire(self, event_name, *args, **opts):
        """Fire an event.

        If an event with the name `event_name` does not exist it will be
        implicitly created and then fired (and likely nothing will happen).

        Only positional arguments can be passed on to event callbacks.

        :param str event_name: The name of the event to hook
        :param sequence args: Optional, arguments passed to the event callbacks
        :param mapping opts: Optional, options passed to the event context
        :returns EventContext: A context manager for the event

        """
        event = self.get_or_make(event_name)
        return EventContext(event, args, opts)


class EventHook:

    """A callback hooked to an event.

    Don't mess with these yourself, they'll be created by and interfaced
    entirely with an EventManager.

    """

    def __init__(self, callback, namespace=None, pre=False, after=None):
        self.callback = callback
        self.namespace = namespace
        self.pre = pre
        self.after = after


class Event:

    """An event, able to be hooked and fired.

    Don't mess with these yourself, they'll be created by and interfaced
    entirely with an EventManager.

    """

    def __init__(self, name):
        self.name = name
        self.hooks = []


class EventContext:

    """A context manager for an event.

    These are created and returned by calling EventManager.fire.

    """

    def __init__(self, event_obj, args, opts):
        self.event = event_obj
        self.args = args
        self.opts = opts

    def __enter__(self):
        if not self.opts.get("no_pre"):
            for hook in self.event.hooks:
                if hook.pre:
                    hook.callback(*self.args)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type or exc_val or exc_tb:
            return
        if not self.opts.get("no_post"):
            for hook in self.event.hooks:
                if not hook.pre:
                    hook.callback(*self.args)

    def now(self):
        """Enter and exit the context manually.

        A convenience method for if you don't need a context manager.  This
        allows you to fire the event on one line:

        >>> EVENTS.fire("some_event").now()

        As opposed to using an empty context, which just looks weird:

        >>> with EVENTS.fire("some_event"):
        ...    pass

        """
        self.__enter__()
        self.__exit__(None, None, None)


# We create a global EventManager here for convenience, and while the server
# will generally only need one to work with, they are NOT singletons and you
# can make more EventManager instances if you like.
EVENTS = EventManager()
