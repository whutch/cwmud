# -*- coding: utf-8 -*-
"""Event handling."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from .logs import get_logger


log = get_logger("events")


class EventManager:

    """A manager for event registration and handling.

    Events are lazily created, when you call ``hook`` or ``fire``, if the
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
        :returns _Event: The existing or newly created event

        """
        event = self._events.get(event_name)
        if not event:
            event = _Event(event_name)
            self._events[event_name] = event
        return event

    def hook(self, event_name, namespace="", callback=None, pre=False):
        """Hook a callback to an event, optionally through a decorator.

        If an event with the name ``event_name`` does not exist it will be
        implicitly created for you.

        If you do not provide ``callback``, this will instead return a
        decorator that will use the decorated function as the callback.

        :param str event_name: The name of the event to hook
        :param str namespace: Optional, a namespace for the hook
        :param function callback: Optional, a callback for the hook
        :param bool pre: Optional, whether to pre- or post-hook the event
        :returns function|None: A decorator to register an event hook callback
                                or None if callback was provided

        """
        def _inner(func):
            event = self.get_or_make(event_name)
            event.hooks.append((func, pre))
            if namespace:
                named_hooks = event.named_hooks.get(namespace)
                if not named_hooks:
                    event.named_hooks[namespace] = named_hooks = []
                named_hooks.append(func)
            return func
        if callback:
            _inner(callback)
        else:
            return _inner

    def unhook(self, event_name, namespace="", callback=None):
        """Unhook callbacks from an event.

        If an event with the name ``event_name`` or a wildcard matching it
        does not exist, nothing happens.

        If neither ``namespace`` nor ``callback`` are provided, all hooks
        will be stripped from the matching event(s). Use cautiously.

        :param str event_name: The name of the event to unhook; it can either
                               be an exact match, "name*" for a following
                               wildcard, or "*" for a total wildcard
        :param str namespace: Optional, a namespace to filter by
        :param function callback: Optional, a function to filter by
        :returns: None

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
            if callback and not namespace:
                # Unhook by callback only
                event.hooks = [(cb, pre) for cb, pre in event.hooks
                               if cb is not callback]
                # We need to ensure that any namespaces pointing to this
                # callback are also cleaned up
                for cbs in event.named_hooks.values():
                    if callback in cbs:
                        cbs.remove(callback)
                event.named_hooks = {name: cbs for name, cbs
                                     in event.named_hooks.items() if cbs}
            elif namespace:
                # Unhook by namespace, with or without a callback
                if namespace in event.named_hooks:
                    hooks = event.named_hooks[namespace]
                    event.hooks = [(cb, pre) for cb, pre in event.hooks
                                   if cb not in hooks
                                   and (cb is callback or callback is None)]
                    if callback:
                        hooks = [hook for hook in hooks
                                 if hook is not callback]
                        event.named_hooks[namespace] = hooks
                    else:
                        del event.named_hooks[namespace]
            else:
                # Just unhook everything (not recommended)
                event.hooks = []
                event.named_hooks = {}

    def fire(self, event_name, *args, **opts):
        """Fire an event.

        If an event with the name ``event_name`` does not exist it will be
        implicitly created and then fired (and likely nothing will happen).

        Only positional arguments can be passed on to event callbacks.

        :param str event_name: The name of the event to hook
        :param sequence args: Optional, arguments passed to the event callbacks
        :param mapping opts: Optional, options passed to the event context
        :returns _EventContext: A context manager for the event

        """
        event = self.get_or_make(event_name)
        return _EventContext(event, args, opts)


class _Event:

    """An event, able to be hooked and fired.

    Don't mess with these yourself, they'll be created by and interfaced
    entirely with an EventManager.

    """

    def __init__(self, name):
        self.name = name
        self.hooks = []
        self.named_hooks = {}


class _EventContext:

    """A context manager for an event.

    These are created and returned by calling EventManager.fire.

    """

    def __init__(self, event_obj, args, opts):
        self.event = event_obj
        self.args = args
        self.opts = opts

    def __enter__(self):
        if not self.opts.get("no_pre"):
            for func, pre in self.event.hooks:
                if pre:
                    func(*self.args)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            raise exc_type(exc_val).with_traceback(exc_tb)
        if not self.opts.get("no_post"):
            for func, pre in self.event.hooks:
                if not pre:
                    func(*self.args)

    def now(self):
        """Enter and exit the context manually.

        A convenience method for if you don't need a context manager. This
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
