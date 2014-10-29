# -*- coding: utf-8 -*-
"""Tests for input request management."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

import pytest

from atria.core.requests import AlreadyExists, RequestManager, Request


class TestRequests:

    """A collection of tests for request management."""

    requests = None
    request_class = None
    request = None

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

            def __init__(self):
                super().__init__()
                pass

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
        type(self).request = self.request_class()
        assert self.request
