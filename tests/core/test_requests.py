# -*- coding: utf-8 -*-
"""Tests for input request management."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

import pytest

from cwmud.core.requests import AlreadyExists, Request, RequestManager
from cwmud.core.utils.funcs import joins


class TestRequests:

    """A collection of tests for request management."""

    requests = None
    request_class = None
    request = None

    # noinspection PyDocstring
    class _FakeSession:

        def __init__(self):
            self._output = []

        def send(self, data, *more, sep=" ", end="\n"):
            return self._output.append(joins(data, *more, sep=sep) + end)

    session = _FakeSession()

    def test_request_manager_create(self):
        """Test that we can create a request manager.

        This is currently redundant, importing the requests package already
        creates one, but we can keep it for symmetry and in case that
        isn't always so.

        """
        type(self).requests = RequestManager()
        assert self.requests

    def test_request_manager_register(self):

        """Test that we can register a new request through a manager."""

        @self.requests.register
        class TestRequest(Request):
            """A test request."""

            def _validate(self, data):
                if not isinstance(data, str):
                    raise self.ValidationFailed("should be a str")
                return data.upper()

        type(self).request_class = TestRequest
        assert "TestRequest" in self.requests._requests

    def test_request_manager_register_already_exists(self):
        """Test that trying to re-register a request fails."""
        with pytest.raises(AlreadyExists):
            self.requests.register(self.request_class)

    def test_request_manager_register_not_request(self):
        """Test that trying to register a non-request fails."""
        with pytest.raises(TypeError):
            self.requests.register(object())

    def test_request_manager_contains(self):
        """Test that we can see if a request manager contains a request."""
        assert "TestRequest" in self.requests
        assert "SomeNonExistentRequest" not in self.requests

    def test_request_manager_get_request(self):
        """Test that we can get a request from a request manager."""
        assert self.requests["TestRequest"] is self.request_class
        with pytest.raises(KeyError):
            self.requests["SomeNonExistentRequest"].resolve("yeah")

    def test_request_create(self):
        """Test that we can create a new request instance."""
        # noinspection PyCallingNonCallable
        type(self).request = self.request_class(self.session, None)
        assert self.request

    def test_request_validation(self):
        """Test that we can validate input for a request."""
        assert Request._validate(self.request, "toot") == "toot"
        assert self.request._validate("toot") == "TOOT"
        with pytest.raises(Request.ValidationFailed):
            self.request._validate(123)

    def test_request_get_prompt(self):
        """Test that we can generate request prompts."""
        # First test without previous input to confirm.
        assert self.request.get_prompt() == self.request.repeat_prompt
        assert self.request.get_prompt() == self.request.repeat_prompt
        self.request.initial_prompt = "Yeah? "
        self.request.flags.drop("prompted")
        assert self.request.get_prompt() == self.request.initial_prompt
        assert self.request.get_prompt() == self.request.repeat_prompt
        # Then test confirmation prompts.
        self.request._confirm = "yeah"
        self.request.confirm = Request.CONFIRM_YES
        assert (self.request.get_prompt() ==
                self.request.confirm_prompt_yn.format(data="yeah"))
        self.request.confirm = Request.CONFIRM_REPEAT
        assert (self.request.get_prompt() ==
                self.request.confirm_prompt_repeat)
        self.request.confirm = "bad confirm type"
        with pytest.raises(ValueError):
            self.request.get_prompt()
        self.request.flags.drop("prompted")

    def test_request_resolve_no_confirm(self):
        """Test that we can resolve a request without confirmation."""
        self.request._confirm = None
        self.request.confirm = None
        assert self.request.resolve("test") is True
        assert not self.request._confirm
        self.request.options["validator"] = lambda value: value
        self.request.callback = lambda session, data: session.send(data)
        assert self.request.resolve("another test") is True
        assert self.request.session._output.pop() == "ANOTHER TEST\n"

    def test_request_resolve_yn_confirm(self):
        """Test that we can resolve a request with yes/no confirmation."""
        self.request.confirm = Request.CONFIRM_YES
        assert self.request.resolve("test") is False
        assert self.request._confirm == "TEST"
        assert self.request.resolve("no") is False
        assert not self.request._confirm
        assert self.request.resolve("test") is False
        assert self.request._confirm == "TEST"
        assert self.request.resolve("yes") is True

    def test_request_resolve_repeat_confirm(self):
        """Test that we can resolve a request with repeat confirmation."""
        self.request._confirm = None
        self.request.confirm = Request.CONFIRM_REPEAT
        assert self.request.resolve(123) is False
        assert not self.request._confirm
        assert self.request.resolve("test") is False
        assert self.request.resolve("testtt") is False
        assert self.request.resolve("test") is False
        assert self.request.resolve(123) is False
        assert self.request.resolve("test") is False
        assert self.request.resolve("test") is True

    def test_request_resolve_invalid_confirm(self):
        """Test that we can detect a bad request confirmation type."""
        self.request.confirm = "bad confirm type"
        with pytest.raises(ValueError):
            self.request.resolve("test")
