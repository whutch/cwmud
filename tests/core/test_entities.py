# -*- coding: utf-8 -*-
"""Tests for entities."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

import pytest

from cwmud.core.entities import Entity, EntityManager
from cwmud.core.pickle import PickleStore
from cwmud.core.utils.exceptions import AlreadyExists


class SomeEntity(Entity):

    """A test subclass of entity."""

    _store = PickleStore("some_entities")
    _uid_code = "S"


@pytest.fixture(scope="module")
def manager():
    """Create an entity manager for all tests to share."""
    return EntityManager()


@pytest.fixture(scope="module")
def entity():
    """Create an entity for all tests to share."""
    return SomeEntity()


class TestEntityManagers:

    """A collection of tests for entity managers."""

    def test_entity_manager_register(self, manager):
        """Test that we can register an entity type with a manager."""
        assert manager.register(SomeEntity) is SomeEntity

    def test_entity_manager_register_bad_type(self, manager):
        """Test that trying to register a non-entity with a manager fails."""
        with pytest.raises(TypeError):
            manager.register(manager)

    def test_entity_manager_register_already_exists(self, manager):
        """Test that trying to re-register an entity type fails."""
        with pytest.raises(AlreadyExists):
            manager.register(SomeEntity)


class TestEntities:

    """A collection of tests for entities."""

    def test_entity_create(self, entity):
        """Test that we can create an entity."""
        assert entity

    def test_entity_load_data_integrity(self):
        """Test loading two copies of an entity from a store transaction."""
        another_entity = SomeEntity()
        uid = another_entity.uid
        assert uid
        assert uid in SomeEntity._instances
        assert another_entity in SomeEntity._instances.values()
        another_entity.save()
        assert uid in SomeEntity._store._transaction
        del another_entity
        # Entity should have been dereferenced and fallen out of instances,
        # an attempt to load it now should fall back to the store transaction.
        assert uid not in SomeEntity._instances.values()
        assert uid in SomeEntity._store._transaction
        another_entity = SomeEntity.get(uid=uid)
        assert another_entity and another_entity.uid
        assert another_entity.uid == uid
        del another_entity
        assert uid not in SomeEntity._instances.values()
        another_copy = SomeEntity.get(uid=uid)
        assert another_copy and another_copy.uid
        assert another_copy.uid == uid
