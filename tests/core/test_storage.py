# -*- coding: utf-8 -*-
"""Tests for storage and data management."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

import pytest

from atria.core.storage import AlreadyExists, DataStoreManager, DataStore


class TestDataStores:

    """A collection of tests for data store management."""

    stores = None
    store_class = None
    store = None
    data = {"yeah": 1, "beep": 2}

    def test_store_manager_create(self):
        """Test that we can create a store manager.

        This is currently redundant, importing the storage package already
        creates one, but we can keep it for symmetry and in case that
        isn't always so.

        """
        type(self).stores = DataStoreManager()
        assert self.stores

    def test_store_manager_register(self):

        """Test that we can register a new store through a store manager."""

        @self.stores.register
        class TestStore(DataStore):

            """A test store."""

            _opens = False

            def __init__(self):
                super().__init__()
                self._stored = {}
                self._opened = False

            @property
            def _is_open(self):
                return self._opened

            def _open(self):
                self._opened = True

            def _close(self):
                self._opened = False

            def _has(self, key):
                return key in self._stored

            def _get(self, key):
                return self._stored[key]

            def _put(self, key, data):
                self._stored[key] = data

            def _delete(self, key):
                del self._stored[key]

        type(self).store_class = TestStore
        assert "TestStore" in self.stores._stores

    def test_store_manager_register_already_exists(self):
        """Test that trying to re-register a store fails."""
        with pytest.raises(AlreadyExists):
            self.stores.register(self.store_class)

    def test_store_manager_register_not_store(self):
        """Test that trying to register a non-store fails."""
        with pytest.raises(TypeError):
            self.stores.register(object())

    def test_store_manager_contains(self):
        """Test that we can see if a store manager contains a store."""
        assert "TestStore" in self.stores
        assert not "SomeNonExistentStore" in self.stores

    def test_store_manager_get_store(self):
        """Test that we can get a store from a store manager."""
        assert self.stores["TestStore"] is self.store_class
        with pytest.raises(KeyError):
            self.stores["SomeNonExistentStore"].has("yeah")

    def test_store_create(self):
        """Test that we can create a new store instance."""
        # noinspection PyCallingNonCallable
        type(self).store = self.store_class()
        assert self.store

    def test_store_opens(self):
        """Test that we can tell if a store opens and closes or not."""
        assert not self.store.opens
        self.store._opens = True
        assert self.store.opens
        self.store._opens = False

    def test_store_is_open(self):
        """Test that we can tell if a store is open or closed."""
        assert not self.store._opens and not self.store._is_open
        assert self.store.is_open
        self.store._opens = True
        assert not self.store.is_open
        self.store._opened = True
        assert self.store.is_open
        self.store._opened = False

    def test_store_open_no_opens(self):
        """Test that opening a store that doesn't open does nothing."""
        self.store._opens = False
        assert not self.store.opens
        assert not self.store._opened
        self.store.open()
        assert not self.store._opened

    def test_store_close_no_opens(self):
        """Test that closing a store that doesn't open does nothing."""
        assert not self.store.opens
        self.store._opened = True
        self.store.close()
        assert self.store._opened

    def test_store_open(self):
        """Test that we can open a store."""
        self.store._opens = True
        self.store._opened = False
        assert self.store.opens
        assert not self.store.is_open
        self.store.open()
        assert self.store.is_open

    def test_store_has_not_found(self):
        """Test that a store doesn't have a non-existent key."""
        assert not self.store.has("test")

    def test_store_get_not_found(self):
        """Test that trying to get a non-existent key from a store fails."""
        with pytest.raises(KeyError):
            self.store.get("test")

    def test_store_delete_not_found(self):
        """Test that trying to delete a non-existent key from a store fails."""
        with pytest.raises(KeyError):
            self.store.delete("test")

    def test_store_pending_no_transaction(self):
        """Test that we can tell that a store has no pending transaction."""
        assert not self.store.pending

    def test_commit_no_transaction(self):
        """Test that committing an empty transaction does nothing."""
        assert not self.store._transaction and not self.store._stored
        self.store.commit()
        assert not self.store._transaction and not self.store._stored

    def test_store_put(self):
        """Test that we can put data into a store's transaction."""
        self.store.put("test", self.data)
        assert "test" in self.store._transaction
        assert self.store._transaction["test"] is self.data
        assert "test" not in self.store._stored

    def test_store_pending(self):
        """Test that we can tell that a store has a pending transaction."""
        assert self.store.pending

    def test_store_has_in_transaction(self):
        """Test that we can tell if a key is in a pending transaction."""
        assert "test" not in self.store._stored
        assert self.store.has("test")

    def test_store_get_from_transaction(self):
        """Test that we can get pending data from a transaction."""
        assert "test" not in self.store._stored
        assert self.store.get("test") is self.data

    def test_store_delete_from_transaction(self):
        """Test that we can delete a key from a pending transaction."""
        assert "test" in self.store._transaction
        self.store.delete("test")
        assert "test" not in self.store._transaction

    def test_store_commit(self):
        """Test that we can commit a store's transaction."""
        assert not self.store._transaction and not self.store._stored
        self.store.put("test", self.data)
        assert "test" in self.store._transaction
        assert "test" not in self.store._stored
        self.store.commit()
        assert not self.store._transaction
        assert "test" in self.store._stored

    def test_store_abort(self):
        """Test that we can abort a store's transaction."""
        assert not self.store._transaction
        self.store.put("test", self.data)
        assert "test" in self.store._transaction
        self.store.abort()
        assert not self.store._transaction

    def test_store_has_in_store(self):
        """Test that we can tell if a key is in a store."""
        assert self.store.has("test")

    def test_store_has_delete_pending(self):
        """Test that a store doesn't 'have' a key that is pending deletion."""
        self.store.delete("test")
        assert not self.store.has("test")

    def test_store_get_delete_pending(self):
        """Test that trying to get a key that is pending deletion fails."""
        assert "test" in self.store._stored
        assert "test" in self.store._transaction
        with pytest.raises(KeyError):
            self.store.get("test")

    def test_store_delete_already_deleting(self):
        """Test that trying to delete a key already pending deletion fails."""
        assert "test" in self.store._stored
        assert "test" in self.store._transaction
        with pytest.raises(KeyError):
            self.store.delete("test")
        self.store.abort()
        assert self.store.has("test")

    def test_store_get_from_store(self):
        """Test that we can get data from a store."""
        assert self.store.get("test") is self.data

    def test_store_delete_from_store(self):
        """Test that we can delete data from a store."""
        assert self.store.has("test")
        self.store.delete("test")
        assert "test" in self.store._transaction
        self.store.commit()
        assert not self.store._transaction
        assert not self.store._stored

    def test_store_close(self):
        """Test that we can close a store with an implied final commit."""
        assert self.store.opens and self.store.is_open
        assert not self.store.has("test")
        self.store.put("test", self.data)
        self.store.close()
        assert self.store.has("test")
        assert not self.store.is_open

    def test_store_close_no_commit(self):
        """Test that we can close a store without the final commit."""
        self.store.open()
        assert self.store.has("test")
        self.store.delete("test")
        self.store.close(commit=False)
        assert "test" in self.store._transaction
        assert not self.store.is_open
