# -*- coding: utf-8 -*-
"""Tests for entities."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from unittest.mock import Mock

import pytest

from cwmud.core.attributes import Attribute, DataBlob
from cwmud.core.entities import ENTITIES, Entity, EntityManager
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

    def test_entity_manager_contains(self, manager):
        """Test that we can check if a manager contains an entity type."""
        assert "SomeEntity" in manager
        assert "NonExistentEntity" not in manager

    def test_entity_manager_getitem(self, manager):
        """Test that we can get an entity from a manager by name."""
        assert manager["SomeEntity"] is SomeEntity
        with pytest.raises(KeyError):
            return manager["NonExistentEntity"]

    def test_entity_manager_save(self, manager):
        """Test that we can save all of a manager's dirty entities."""
        mock1 = Mock(is_savable=True, is_dirty=False)
        SomeEntity._instances["mock1"] = mock1
        mock2 = Mock(is_savable=True, is_dirty=False)
        SomeEntity._instances["mock2"] = mock2
        # First test with no dirty entities.
        manager.save()
        assert not mock1.save.called
        assert not mock1.save.called
        # Then test with a dirty entity.
        mock1.is_dirty = True
        manager.save()
        assert mock1.save.called
        assert not mock2.save.called


class TestEntities:

    """A collection of tests for entities."""

    def test_entity_register_blob(self):
        """Test that we can register a data blob on an entity type."""
        class TestBlob(DataBlob):
            """A test blob."""
        SomeEntity.register_blob("test_blob")(TestBlob)
        with pytest.raises(AlreadyExists):
            SomeEntity.register_blob("test_blob")(TestBlob)
        with pytest.raises(TypeError):
            SomeEntity.register_blob("another_blob")(None)

    def test_entity_register_attr(self):
        """Test that we can register an attribute on an entity type."""
        class TestAttribute(Attribute):
            """A test attribute."""
        SomeEntity.register_attr("test_attr")(TestAttribute)
        with pytest.raises(AlreadyExists):
            SomeEntity.register_attr("test_attr")(TestAttribute)
        with pytest.raises(TypeError):
            SomeEntity.register_attr("another_attr")(None)

    def test_entity_cache(self):
        """Test entity caching and ejection."""
        SomeEntity.register_cache("test", size=2)
        with pytest.raises(AlreadyExists):
            SomeEntity.register_cache("test")
        # Test that insertions over the size limit will eject one.
        mocks = [Mock(), Mock(), Mock()]
        SomeEntity._caches["test"][0] = mocks[0]
        SomeEntity._caches["test"][1] = mocks[1]
        assert 0 in SomeEntity._caches["test"]
        assert not mocks[0].save.called
        SomeEntity._caches["test"][2] = mocks[2]
        assert 0 not in SomeEntity._caches["test"]
        assert mocks[0].save.called

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
