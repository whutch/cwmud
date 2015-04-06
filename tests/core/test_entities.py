# -*- coding: utf-8 -*-
"""Tests for entities."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2015 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from atria.core.entities import Entity


class TestEntities:

    """A collection of tests for entities."""

    entity = None

    def test_entity_create(self):
        """Test that we can create an entity."""
        type(self).entity = Entity()
