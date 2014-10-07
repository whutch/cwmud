# -*- coding: utf-8 -*-
"""Tests for utility exception classes."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from atria.core.utils import exceptions


def test_already_exists():
    """Test that raising AlreadyExists works as intended."""
    try:
        raise exceptions.AlreadyExists("test", old=1, new=2)
    except exceptions.AlreadyExists as exc:
        assert exc.key and exc.old and exc.new
