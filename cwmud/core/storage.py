# -*- coding: utf-8 -*-
"""Storage and data management."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from collections import OrderedDict
from copy import deepcopy
from itertools import chain

from .logs import get_logger
from .utils.exceptions import AlreadyExists
from .utils.funcs import joins


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
        :raises TypeError: If `store` is not an instance of DataStore

        """
        if not isinstance(store, DataStore):
            raise TypeError("must be instance of DataStore to register")
        if name in self._stores:
            raise AlreadyExists(name, self._stores[name], store)
        self._stores[name] = store
        return store

    def initialize(self):
        """Initialize all registered data stores."""
        log.info("Initializing stores.")
        for store in self._stores.values():
            store.initialize()
            store.build_indexes()

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
            log.debug("Commit %s items from %s transactions.",
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
            log.debug("Abort %s items from %s transactions.",
                      item_count, transaction_count)


class DataStore:

    """A store for data."""

    # Whether this data store needs to be opened and closed.
    _opens = False

    def __init__(self):
        """Create a new data store."""
        self._transaction = OrderedDict()
        # Indexes is a nested dictionary, keyed first by data key, and
        # then by value, each containing a set of store keys with that value.
        self._indexes = {}
        self._unique_keys = set()

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

    def initialize(self):
        """Initialize this store.

        Override this on subclasses to perform any setup needed.

        """

    def add_index(self, key, unique=False):
        """Add an index to this store.

        Adding an index does not automatically rebuild the indexes;
        if you are adding an index after the server has booted, you will
        need to call store.build_indexes() yourself.

        :param str key: The data key to index
        :param bool unique: Whether the given key is unique to each blob
        :returns None:

        """
        if key in self._indexes:
            log.warning("Tried to add existing index '%s' to %s", key, self)
            return
        self._indexes[key] = {}
        if unique:
            self._unique_keys.add(key)

    def build_indexes(self):
        """Build the indexes for this store using all stored data."""
        for key in self._keys():
            data = self._get(key)
            self.update_indexes(key, data, prune=False)

    def update_indexes(self, key, data, prune=True):
        """Update the indexes for this store with data for one key.

        :param str key: The storage key for the data
        :param dict data: The data to update the indexes with
        :param bool prune: Whether to load any existing data from the store
                           so that old values can be removed.
        :returns None

        """
        old_data = {}
        if prune and self._has(key):
            old_data = self._get(key)
        for index_key, index in self._indexes.items():
            if data and index_key in data:
                value = data[index_key]
                if value not in index:
                    index[value] = set()
                elif index[value] and index_key in self._unique_keys:
                    raise KeyError("unique key '{}' already has value '{}'"
                                   .format(index_key, index[value]))
                index[value].add(key)
            else:
                value = None
            if prune:
                old_value = old_data.get(index_key)
                if old_value != value and old_value in index:
                    index[old_value].discard(key)

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
        try:
            return self._has(key)
        except (KeyError, TypeError):
            return False

    def _find_in_store(self, ignore_keys=(), **key_value_pairs):
        found = set()
        for key in self._keys():
            if key in ignore_keys:
                continue
            data = self._get(key)
            for _key, _value in key_value_pairs.items():
                if _key not in data or data[_key] != _value:
                    break
            else:
                found.add(key)
        return found

    def _find_in_index(self, **key_value_pairs):
        found = set()
        pairs = list(key_value_pairs.items())
        if not pairs:
            return found
        # Add all the items that match the first key/value pair.
        key, value = pairs.pop()
        if key in self._indexes and value in self._indexes[key]:
            found.update(self._indexes[key][value])
        # Then remove all the items that don't match all the other pairs.
        if pairs:
            for key, value in pairs:
                if not found:
                    # There's nothing left to check against.
                    break
                if key in self._indexes and value in self._indexes[key]:
                    found.intersection_update(self._indexes[key][value])
        # Anything left matched all key/value pairs.
        return found

    def _find_in_transaction(self, ignore_keys=(), **key_value_pairs):
        found = set()
        for key, data in self._transaction.items():
            if key in ignore_keys:
                continue
            for _key, _value in key_value_pairs.items():
                if data is None or _key not in data or data[_key] != _value:
                    break
            else:
                found.add(key)
        return found

    def find(self, transaction=True, ignore_keys=(), **key_value_pairs):
        """Find data blobs by one or more keyed values.

        :param bool transaction: Whether to check the transaction
        :param iterable ignore_keys: A sequence of keys to ignore
        :param iterable key_value_pairs: Pairs of keys and values to
                                         match against
        :returns list: A list of keys to matching blobs, if any

        """
        # Checking the indexes only makes sense if *all* the key/value
        # pairs are actually indexed.
        if all(map(self._indexes.get, key_value_pairs)):
            found = self._find_in_index(**key_value_pairs)
        else:
            found = self._find_in_store(ignore_keys=ignore_keys,
                                        **key_value_pairs)
        if transaction:
            # Remove any keys already found that are in the transaction.
            found.difference_update(self._transaction)
            # And then add them back only if they match our values.
            found.update(self._find_in_transaction(ignore_keys=ignore_keys,
                                                   **key_value_pairs))
        return list(found)

    def get(self, key=None, default=None, transaction=True, **key_value_pairs):
        """Get data from the store by one or more of its attribute values.

        :param key: The key to get; if given `key_value_pairs` will be ignored
        :param default: A default value to return if no entity is found; if
                        default is an exception, it will be raised instead
        :param bool transaction: Whether to check the transaction
        :param iterable key_value_pairs: Pairs of keys and values to
                                         match against
        :returns dict: A matching data blob, or default
        :raises KeyError: If more than one key matches the given values

        """
        if key is None:
            matches = self.find(transaction=transaction, **key_value_pairs)
            if len(matches) > 1:
                raise KeyError(joins("get returned more than one match:",
                                     matches, "using values", key_value_pairs))
            if matches:
                key = matches[0]
        if key:
            if transaction and key in self._transaction:
                data = self._transaction[key]
                if data is not None:
                    return deepcopy(data)
            else:
                return self._get(key)
        # Nothing was found.
        if isinstance(default, type) and issubclass(default, Exception):
            raise default
        else:
            return default

    def put(self, key, data):
        """Put data into the store.

        This does not immediately put the data into the store, but will
        queue it for saving in the transaction.

        :param hashable key: The key to store the data under
        :param dict data: The data to store
        :returns None:

        """
        try:
            self._transaction[key] = data
        except ReferenceError:
            # Suppress occasional ignored exception in OrderedDict internals.
            pass

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
        # We need to update indexes first, otherwise we won't be able to
        # prune an old value from an index.  We also want any exceptions
        # triggered by the indexing to happen before we save everything.
        for key, data in self._transaction.items():
            self.update_indexes(key, data)
        while self._transaction:
            key, data = self._transaction.popitem(last=False)
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
