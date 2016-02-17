# -*- coding: utf-8 -*-
"""Input request management."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from .logs import get_logger
from .utils.exceptions import AlreadyExists
from .utils.funcs import joins
from .utils.mixins import HasFlags, HasFlagsMeta, HasWeaks, HasWeaksMeta


log = get_logger("requests")


class RequestManager:

    """A manager for request template registration.

    This is a convenience manager and is not required for the server to
    function.  All of its functionality can be achieved by subclassing,
    instantiating, and referencing requests directly.

    """

    def __init__(self):
        """Create a new data request manager."""
        self._requests = {}

    def __contains__(self, request):
        return request in self._requests

    def __getitem__(self, request):
        return self._requests[request]

    def register(self, request):
        """Register a request template.

        This method can be used to decorate a Request class.

        :param Request request: The request template to be registered
        :returns Request: The registered request template
        :raises AlreadyExists: If a request with that class name already exists
        :raises TypeError: If the supplied or decorated class is not a
                           subclass of Request

        """
        if (not isinstance(request, type) or
                not issubclass(request, Request)):
            raise TypeError("must be subclass of Request to register")
        name = request.__name__
        if name in self._requests:
            raise AlreadyExists(name, self._requests[name], request)
        self._requests[name] = request
        return request


class _RequestMeta(HasFlagsMeta, HasWeaksMeta):
    # To avoid multiple metaclass errors.
    pass


class Request(HasFlags, HasWeaks, metaclass=_RequestMeta):

    """A request for input from a client."""

    # Constants, don't change these.
    CONFIRM_YES = 1
    CONFIRM_REPEAT = 2

    # Defaults, override these on subclasses.
    initial_prompt = None
    repeat_prompt = "? "
    confirm = None
    confirm_prompt_yn = "'{data}', is that correct? (Y/N) "
    confirm_prompt_repeat = "Repeat to confirm: "

    def __init__(self, session, callback, **options):
        """Create an input request from this template."""
        super().__init__()
        self.session = session
        self.callback = callback
        self.options = options.copy()
        self._confirm = None

    @property
    def session(self):
        """Return the current session for this request."""
        return self._get_weak("session")

    @session.setter
    def session(self, new_session):
        """Set the current session for this request.

        :param Session new_session: The session tied to this request
        :returns None:

        """
        self._set_weak("session", new_session)

    class ValidationFailed(Exception):
        """An exception signaling that client input failed to validate."""

        def __init__(self, msg):
            self.msg = msg

    def _validate(self, data):
        """Validate client input toward this request.

        Override this to perform any custom validation on subclasses.  This
        method should either return the validated data or raise the
        ValidationFailed exception with an error message that will be sent to
        the client, any other exceptions will be re-raised.  The data can be
        changed before returning it to allow for normalization, etc.

        """
        return data

    def get_prompt(self):
        """Generate the current prompt for this request."""
        if self._confirm:
            confirm = self.options.get("confirm") or self.confirm
            if confirm == Request.CONFIRM_YES:
                prompt = (self.options.get("confirm_prompt_yn") or
                          self.confirm_prompt_yn)
            elif confirm == Request.CONFIRM_REPEAT:
                prompt = (self.options.get("confirm_prompt_repeat") or
                          self.confirm_prompt_repeat)
            else:
                raise ValueError(joins("bad value for request option "
                                       "'confirm':", confirm))
            return prompt.format(data=self._confirm)
        else:
            if not self.flags.has("prompted"):
                self.flags.add("prompted")
                initial_prompt = (self.options.get("initial_prompt") or
                                  self.initial_prompt)
                if initial_prompt:
                    return initial_prompt
            return self.options.get("repeat_prompt") or self.repeat_prompt

    def resolve(self, data):

        """Attempt to resolve this request with input from a client.

        :param str data: The data to try and resolve this request with
        :returns bool: Whether this request successfully resolved or not

        """

        resolved = False
        error = None
        confirm = self.options.get("confirm") or self.confirm
        errors = self.options.get("errors", {})

        def _validate(_data):
            validator = self.options.get("validator")
            if validator:
                _data = validator(_data)
            return self._validate(_data)

        if self._confirm:
            # They've already sent valid input, we just need to confirm it.
            if confirm == Request.CONFIRM_YES:
                if not "yes".startswith(data.lower()):
                    error = errors.get("no", "Alright, what then?")
            elif confirm == Request.CONFIRM_REPEAT:
                try:
                    # We have to pass the repeated input through validation
                    # so that any normalization that happened to the original
                    # input happens to the repeated input as well.
                    data = _validate(data)
                except Request.ValidationFailed:
                    # We don't really care if repeated input won't validate,
                    # we just want to know if it isn't the same, and the
                    # original data can't be None, so..
                    data = None
                finally:
                    if data != self._confirm:
                        error = errors.get("mismatch", "Input mismatch.")
            else:
                raise ValueError(joins("bad value for request option "
                                       "'confirm':", confirm))
            if error is None:
                # Confirmation passed, request resolved.
                resolved = True
                # Make sure that the original input gets sent to the callback.
                data = self._confirm

        else:
            # We're not confirming anything yet, do initial validation and
            # then figure out if we need to confirm or not.
            try:
                data = _validate(data)
                if confirm:
                    # We need to confirm this input, so store it for now and
                    # leave the request unresolved.  The confirmation prompt
                    # will be sent by get_prompt at the end of this poll.
                    self._confirm = data
                else:
                    # We don't need to confirm this input, request resolved.
                    resolved = True
            except Request.ValidationFailed as exc:
                error = exc.msg

        if resolved and callable(self.callback):
            self.callback(self.session, data)
        elif error is not None:
            if self._confirm:
                # Confirmation failed, so start over.
                self._confirm = None
            self.session.send(error)
        return resolved


# We create a global RequestManager here for convenience, and while the
# server will generally only need one to work with, they are NOT singletons
# and you can make more RequestManager instances if you like.
REQUESTS = RequestManager()


@REQUESTS.register
class RequestNumber(Request):

    """A request for a number.

    :param int min: Optional, a minimum value for the number
    :param int max: Optional, a maximum value for the number

    """

    def _validate(self, data):
        if not data.isdigit():
            raise Request.ValidationFailed("Input must be a number.")
        data = int(data)
        min_val = self.options.get("min")
        if min_val and data < min_val:
            raise Request.ValidationFailed(joins(
                "Input must be at least ", min_val, ".", sep=""))
        max_val = self.options.get("max")
        if max_val and data < max_val:
            raise Request.ValidationFailed(joins(
                "Input cannot be more than ", max_val, ".", sep=""))
        return data


@REQUESTS.register
class RequestString(Request):

    """A request for a string.

    :param int min_len: Optional, a minimum length for the string
    :param int max_len: Optional, a maximum length for the string

    """

    def _validate(self, data):
        min_len = self.options.get("min_len")
        if min_len and len(data) < min_len:
            raise Request.ValidationFailed(joins(
                "Input must be at least", min_len, "characters long."))
        max_len = self.options.get("max_len")
        if max_len and len(data) > max_len:
            raise Request.ValidationFailed(joins(
                "Input cannot be more than", max_len, "characters long."))
        return data
