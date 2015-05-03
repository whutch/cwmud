# -*- coding: utf-8 -*-
"""Storage and data management."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2015 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from collections import OrderedDict
from itertools import chain

from .logs import get_logger
from .utils.exceptions import AlreadyExists


log = get_logger("storage")


# noinspection PyProtectedMember
class DataStoreManager:

    """A manager for data store registration."""

    def __init__(self):
        """Create a new data store manager."""
        self._stores = {}

    def __contains__(self, store):
        return store in self._stores

    def __getitem__(self, store):
        return self._stores[store]

    def register(self, name, store):
        """Register a data store.

        :param str name: The name of the data store
        :param DataStore store: The data store to be registered
        :returns DataStore: The registered data store
        :raises AlreadyExists: If a store with that name already exists
        :raises TypeError: If `store` is not an instance of DataStore.

        """
        if not isinstance(store, DataStore):
            raise TypeError("must be instance of DataStore to register")
        if name in self._stores:
            raise AlreadyExists(name, self._stores[name], store)
        self._stores[name] = store
        return store

    def commit(self):
        """Commit the transactions of all registered data stores."""
        item_count = 0
        transaction_count = 0
        for store in self._stores.values():
            if store.pending:
                item_count += len(store._transaction)
                transaction_count += 1
                store.commit()
        if item_count or transaction_count:
            log.info("Commit %s items from %s transactions.",
                     item_count, transaction_count)

    def abort(self):
        """Abort the transactions of all registered data stores."""
        item_count = 0
        transaction_count = 0
        for store in self._stores.values():
            if store.pending:
                item_count += len(store._transaction)
                transaction_count += 1
                store.abort()
        if item_count or transaction_count:
            log.info("Abort %s items from %s transactions.",
                     item_count, transaction_count)


class DataStore:

    """A store for data."""

    # Whether this data store needs to be opened and closed.
    _opens = False

    def __init__(self):
        """Create a new data store."""
        self._transaction = OrderedDict()

    def _is_open(self):  # pragma: no cover
        raise NotImplementedError

    def _open(self):  # pragma: no cover
        raise NotImplementedError

    def _close(self):  # pragma: no cover
        raise NotImplementedError

    def _keys(self):  # pragma: no cover
        raise NotImplementedError

    def _has(self, key):  # pragma: no cover
        raise NotImplementedError

    def _get(self, key):  # pragma: no cover
        raise NotImplementedError

    def _put(self, key, data):  # pragma: no cover
        raise NotImplementedError

    def _delete(self, key):  # pragma: no cover
        # Deleting objects from a store should be kept simple; it is not
        # a store's responsibility to care about objects that link to
        # each others' keys, etc.
        raise NotImplementedError

    @property
    def opens(self):
        """Return whether this store opens and closes or not."""
        return self._opens

    @property
    def is_open(self):
        """Return whether this store is open or not."""
        if not self._opens:
            return True
        return self._is_open

    def open(self):
        """Open this data store."""
        if not self._opens:
            return
        self._open()

    def close(self, commit=True):
        """Close this data store.

        :param bool commit: Whether to commit the transaction before closing
        :returns None:

        """
        if not self._opens:
            return
        if commit:
            self.commit()
        self._close()

    # CHEESEBURGER DELIGHT
    # RED SKY AT NIGHT
    # CHEESEBURGER MOURNING
    # SAILORS TAKE WARNING

    def keys(self):
        """Return an iterator through this store's keys."""
        # We also need to include keys that are only in the transaction and
        # not yet saved to the store.
        trans_keys = self._transaction.keys()
        return chain(trans_keys, (key for key in self._keys()
                                  if key not in trans_keys))

    def has(self, key):
        """Return whether this store has a given key or not.

        :param hashable key: The key to check for
        :returns bool: Whether the key exists or not

        """
        if key in self._transaction:
            return self._transaction[key] is not None
        return self._has(key)

    def get(self, key):
        """Fetch data from the store.

        :param hashable key: The key of the data to fetch
        :returns dict: The fetched data
        :raises KeyError: If the given key does not exist in the store

        """
        if key in self._transaction:
            pending_data = self._transaction[key]
            if pending_data is None:
                raise KeyError(key)
            return pending_data
        else:
            if not self.has(key):
                raise KeyError(key)
            return self._get(key)

    def put(self, key, data):
        """Put data into the store.

        This does not immediately put the data into the store, but will
        queue it for saving in the transaction.

        :param hashable key: The key to store the data under
        :param dict data: The data to store
        :returns None:

        """
        self._transaction[key] = data

    def delete(self, key):
        """Delete date from the store.

        This does not immediately delete the data from the store, but will
        queue it for removal in the transaction.

        :param hashable key: The key of the data to delete
        :returns None:
        :raises KeyError: If the given key does not exist in the store

        """
        if key in self._transaction:
            if self._transaction[key] is None:
                raise KeyError(key)
            del self._transaction[key]
        else:
            if not self.has(key):
                raise KeyError(key)
            # Storing None for a key in the transaction will tell the store
            # to delete that key during the next commit.
            self._transaction[key] = None

    @property
    def pending(self):
        """Return whether this store has a pending transaction."""
        return bool(self._transaction)

    def commit(self):
        """Commit the current data transaction."""
        if not self._transaction:
            return
        while self._transaction:
            key, data = self._transaction.popitem()
            if data is None:
                if self._has(key):
                    self._delete(key)
            else:
                self._put(key, data)

    def abort(self):
        """Abort the current data transaction."""
        self._transaction.clear()


# We create a global DataStoreManager here for convenience, and while the
# server will generally only need one to work with, they are NOT singletons
# and you can make more DataStoreManager instances if you like.
STORES = DataStoreManager()
