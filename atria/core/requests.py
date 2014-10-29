# -*- coding: utf-8 -*-
"""Input request management."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from .logs import get_logger
from .utils.exceptions import AlreadyExists


log = get_logger("requests")


class RequestManager:

    """A manager for request template registration.

    This is a convenience manager and is not required for the server to
    function. All of its functionality can be achieved by subclassing,
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
                           subclass of Request.

        """
        if (not isinstance(request, type) or
                not issubclass(request, Request)):
            raise TypeError("must be subclass of Request to register")
        name = request.__name__
        if name in self._requests:
            raise AlreadyExists(name, self._requests[name], request)
        self._requests[name] = request
        return request


class Request:

    """An input request."""

    def __init__(self):
        """Create an input request from this template."""
        pass
