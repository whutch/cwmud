# -*- coding: utf-8 -*-
"""Entities, the base of all complex MUD objects."""
# Part of Clockwork MUD Server (https://github.com/whutch/cwmud)
# :copyright: (c) 2008 - 2016 Will Hutcheson
# :license: MIT (https://github.com/whutch/cwmud/blob/master/LICENSE.txt)

from copy import deepcopy
from weakref import WeakValueDictionary

from pylru import lrucache

from .attributes import Attribute, DataBlob, Unset
from .json import JSONStore
from .logs import get_logger
from .storage import STORES
from .timing import TIMERS
from .utils.exceptions import AlreadyExists
from .utils.funcs import class_name, int_to_base_n, joins
from .utils.mixins import (HasFlags, HasFlagsMeta, HasTags,
                           HasWeaks, HasWeaksMeta)


log = get_logger("entities")


# Do NOT change these after your server has started generating UIDs or you
# risk running into streaks of duplicate UIDs.
_uid_timecode_multiplier = 10000
_uid_timecode_charset = ("0123456789aAbBcCdDeEfFgGhHijJkKLmM"
                         "nNopPqQrRstTuUvVwWxXyYzZ")
# I left out "I", "l", "O", and "S" to make time codes easier to distinguish
# regardless of font.  If my base 58 math is to be believed, this character set
# should generate eight-digit time codes with 100 microsecond precision until
# October 25th, 2375, and then nine-digit codes well into the 26th millennium.


class EntityManager:

    """A manager for entity types."""

    def __init__(self):
        """Create a new entity manager."""
        self._entities = {}

    def __contains__(self, name):
        return name in self._entities

    def __getitem__(self, name):
        return self._entities[name]

    def register(self, entity):
        """Register an entity type.

        This method can be used to decorate an Entity class.

        :param Entity entity: The entity to be registered
        :returns Entity: The registered entity
        :raises AlreadyExists: If an entity with that class name already exists
        :raises TypeError: If the supplied or decorated class is not a
                           subclass of Entity

        """
        if (not isinstance(entity, type) or
                not issubclass(entity, Entity)):
            raise TypeError("must be subclass of Entity to register")
        name = entity.__name__
        if name in self._entities:
            raise AlreadyExists(name, self._entities[name], entity)
        self._entities[name] = entity
        return entity

    def save(self):
        """Save the dirty instances of all registered entities."""
        count = 0
        for entity in self._entities.values():
            # noinspection PyProtectedMember
            for instance in entity._instances.values():
                if instance.is_savable and instance.is_dirty:
                    instance.save()
                    count += 1
        if count:
            log.debug("Saved %s dirty entities.", count)


# noinspection PyDocstring
class _EntityMeta(HasFlagsMeta, HasWeaksMeta):

    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        cls._base_blob = type(name + "BaseBlob", (DataBlob,), {})
        cls._instances = WeakValueDictionary()
        cls._caches = {}
        # noinspection PyUnresolvedReferences
        cls.register_cache("uid")

    def register_blob(cls, name):
        """Decorate a data blob to register it on this entity.

        :param str name: The name of the field to store the blob
        :returns DataBlob: The decorated blob
        :raises AlreadyExists: If the given name already exists as an attr
        :raises TypeError: If the supplied or decorated class is not a
                           subclass of DataBlob

        """
        if hasattr(cls, name):
            raise AlreadyExists(name, getattr(cls, name))

        # noinspection PyProtectedMember
        def _inner(blob_class):
            if (not isinstance(blob_class, type) or
                    not issubclass(blob_class, DataBlob)):
                raise TypeError("must be subclass of DataBlob to register")
            # noinspection PyUnresolvedReferences
            cls._base_blob._blobs[name] = blob_class
            prop = property(lambda s: s._base_blob._blobs[name])
            setattr(cls, name, prop)
            return blob_class

        return _inner

    def register_attr(cls, name):
        """Decorate an attribute to register it on this entity.

        :param str name: The name of the field to store the attribute
        :returns Attribute: The decorated attribute
        :raises AlreadyExists: If the given name already exists as an attr
        :raises TypeError: If the supplied or decorated class is not a
                           subclass of Attribute

        """
        if hasattr(cls, name):
            raise AlreadyExists(name, getattr(cls, name))

        # noinspection PyProtectedMember
        def _inner(attr_class):
            if (not isinstance(attr_class, type) or
                    not issubclass(attr_class, Attribute)):
                raise TypeError("must be subclass of Attribute to register")
            # noinspection PyUnresolvedReferences
            cls._base_blob._attrs[name] = attr_class
            getter = lambda s: s._base_blob._get_attr_val(name)
            setter = (lambda s, v: s._base_blob._set_attr_val(name, v)
                      if not attr_class._read_only else None)
            setattr(cls, name, property(getter, setter))
            return attr_class

        return _inner

    @staticmethod
    def _cache_eject_callback(key, entity):
        """A callback for when entities are ejected from a cache.

        When an entity is dumped from all of it's caches, there's a chance
        it could fall out of scope before every being saved, so we save it
        on ejection to be sure.

        :param key: The ejected entity's cache key
        :param Entity entity: The ejected entity
        :return None:

        """
        entity.save()

    def register_cache(cls, key, size=512):
        """Create a new cache for this entity, keyed by attribute.

        Currently these caches are not searched, they merely serve as another
        reference to keep their entries in _instances alive.

        There is support for caching UIDs and Attribute values when
        they change, if you want to register anything else (such as bare
        properties not tied to an Attribute) then you'll need to make sure to
        update the cache yourself when their values change.

        :param str key: The attribute name to use as a key
        :param int size: The size of the cache to create
        :returns None:
        :raises KeyError: If a cache already exists for `key`

        """
        if key in cls._caches:
            raise AlreadyExists(key, cls._caches[key])
        cache = lrucache(size, cls._cache_eject_callback)
        cls._caches[key] = cache
        # Fill the cache with any existing entity data.
        for entity in cls._instances.values():
            attr_value = getattr(entity, key)
            if attr_value not in (None, Unset):
                if attr_value not in cache:
                    cache[attr_value] = {entity}
                else:
                    cache[attr_value].add(entity)


class Entity(HasFlags, HasTags, HasWeaks, metaclass=_EntityMeta):

    """The base of all persistent objects in the game."""

    _store = STORES.register("entities", JSONStore("entities"))
    _uid_code = "E"

    type = "entity"

    # These are overridden in the metaclass, I just put them here
    # to avoid a lot of unresolved reference errors in IDE introspection.
    _base_blob = None
    _instances = {}
    _caches = {}

    __uid_timecode = 0  # Used internally for UID creation.

    def __init__(self, data=None, active=False, savable=True):
        super().__init__()

        def _build_base_blob(cls, blob=self._base_blob(self), checked=set()):
            # Recursively update our base blob with the blobs of our parents.
            for base in cls.__bases__:
                _build_base_blob(base)
                # We don't need to do anything with the blob returned by this
                # because we're abusing the mutability of default arguments.
            if issubclass(cls, Entity):
                if cls not in checked:  # pragma: no cover
                    # noinspection PyProtectedMember
                    blob._update(cls._base_blob(self))
                    checked.add(cls)
            return blob

        self._base_blob = _build_base_blob(self.__class__)
        self._dirty = False
        self._savable = savable

        # Never, ever manually change an object's UID! There are no checks
        # for removing the old UID from the store, updating UID links, or
        # anything else like that.  Bad things will happen!
        self._uid = None
        if data and "uid" in data:
            self._set_uid(data.pop("uid"))
        else:
            self._set_uid(self.make_uid())

        # An active entity is considered "in play", inactive entities are
        # hidden from the game world.
        self.active = active

        if data is not None:
            self.deserialize(data)

    def __repr__(self):
        return joins("Entity<", self.uid, ">", sep="")

    def __hash__(self):
        if not self.uid:
            raise ValueError("cannot hash entity with no uid")
        return hash(self.uid)

    def __eq__(self, other):
        if not hasattr(other, "uid") or self.uid != other.uid:
            return False
        else:
            return True

    @property
    def uid(self):
        """Return this entity's UID."""
        return self._uid

    def _set_uid(self, uid):
        """Set this entity's UID.

        To ensure cache integrity, this should be the only place that an
        entity's UID is updated.  This *only* updates references in the
        internal caches, do not rely on it to change anything in the store
        or any other external references (links from other entities).

        """
        cache = self._caches.get("uid")
        if self._uid is not None:
            if self._uid in self._instances:
                del self._instances[self._uid]
            if self._uid in cache:
                del cache[self._uid]
        self._uid = uid
        self._instances[uid] = self
        cache[uid] = {self}

    @property
    def is_dirty(self):
        """Return whether this entity is dirty and needs to be saved."""
        return self._dirty

    @property
    def is_savable(self):
        """Return whether this entity can be saved."""
        return self._store and self._savable

    def _flags_changed(self):
        self.dirty()

    def _tags_changed(self):
        self.dirty()

    def dirty(self):
        """Mark this entity as dirty so that it will be saved."""
        self._dirty = True

    def serialize(self):
        """Create a sanitized dict from the data on this entity.

        :returns dict: The serialized data

        """
        data = self._base_blob.serialize()
        data["type"] = class_name(self)
        data["uid"] = self._uid
        data["flags"] = self.flags.as_tuple
        data["tags"] = deepcopy(self.tags.as_dict)
        return data

    def deserialize(self, data):
        """Update this entity's data using values from a dict.

        :param dict data: The data to deserialize
        :returns None:

        """
        if "type" in data:
            del data["type"]
        if "uid" in data:
            self._set_uid(data.pop("uid"))
        if "flags" in data:
            self.flags.add(*data.pop("flags"))
        if "tags" in data:
            self.tags.clear()
            self.tags.update(data.pop("tags"))
        self._base_blob.deserialize(data)

    @classmethod
    def reconstruct(cls, data):
        """Reconstruct an entity from a dict of its data.

        The given `data` must include a "type" key with the name of a
        registered Entity class as its value.

        This differs from the deserialize method in that this method will
        return an entity created from a class specified in the data, rather
        than merging the data into an existing instance of a (potentially
        different) class.

        :param dict data: The data to reconstruct the entity from
        :returns Entity: The reconstructed entity instance
        :raises KeyError: If `data` has no "type" key or the value of the
                          given key is not a registered Entity class

        """
        entity_name = data.pop("type", None)
        if not entity_name or entity_name not in ENTITIES:
            raise KeyError("failed to reconstruct entity: bad class key")
        entity = ENTITIES[entity_name](data)
        log.debug("Reconstructed %s (%s)", entity, entity.uid)
        return entity

    @classmethod
    def make_uid(cls):
        """Create a UID for this entity.

        UIDs are in the form "C-TTTTTTTT", where C is the entity code and T
        is the current time code.  (Ex. "E-6jQZ4zvH")

        :returns str: The new UID

        """
        big_time = TIMERS.time * _uid_timecode_multiplier
        if big_time > Entity.__uid_timecode:
            Entity.__uid_timecode = big_time
        else:
            Entity.__uid_timecode += 1
        timecode_string = int_to_base_n(Entity.__uid_timecode,
                                        _uid_timecode_charset)
        uid = "-".join((cls._uid_code, timecode_string))
        return uid

    @classmethod
    def _find_in_cache(cls, ignore_keys=(), **attr_value_pairs):
        found = set()
        for key, entity in cls._instances.items():
            if key in ignore_keys:
                continue
            for attr, value in attr_value_pairs.items():
                if getattr(entity, attr) != value:
                    break
            else:
                found.add(entity)
        return found

    @classmethod
    def find(cls, cache=True, store=True, subclasses=True,
             ignore_keys=(), **attr_value_pairs):
        """Find one or more entities by one of their attribute values.

        :param bool cache: Whether to check the _instances cache
        :param bool store: Whether to check the store
        :param bool subclasses: Whether to check subclasses as well
        :param iterable ignore_keys: A sequence of keys to ignore
        :param iterable attr_value_pairs: Pairs of attributes and values to
                                          match against
        :returns list: A list of found entities, if any
        :raises SyntaxError: If both `cache` and `store` are False

        """
        if not cache and not store:
            raise SyntaxError("can't find without cache or store")
        found = set()
        # We might be recursing from a parent class, so if they passed
        # us an existing set we want to use the same one.
        if ignore_keys == ():
            ignore_keys = set()
        elif not isinstance(ignore_keys, set):
            ignore_keys = set(ignore_keys)
        if cache:
            found.update(cls._find_in_cache(ignore_keys=ignore_keys,
                                            **attr_value_pairs))
            ignore_keys.update(cls._instances.keys())
            if subclasses:
                for subclass in cls.__subclasses__():
                    found.update(subclass.find(store=False,
                                               ignore_keys=ignore_keys,
                                               **attr_value_pairs))
        if store:
            found_uids = cls._store.find(ignore_keys=ignore_keys,
                                         **attr_value_pairs)
            found.update([cls.reconstruct(cls._store.get(uid))
                          for uid in found_uids])
            ignore_keys.update(cls._store.keys())
            if subclasses:
                for subclass in cls.__subclasses__():
                    found.update(subclass.find(cache=False,
                                               ignore_keys=ignore_keys,
                                               **attr_value_pairs))
        return list(found)

    @classmethod
    def find_relations(cls, **attr_value_pairs):
        """Find one or more entities by a relation to another entity.

        The purpose of this versus `find` is to match related entities by
        direct reference (in the cache) or by UID (in the store) in one call.

        :param iterable attr_value_pairs: Pairs of attributes and values to
                                          match against
        :returns list: A list of found entities, if any
        :raises TypeError: If any of the pairs' values are not entity instances

        """
        found = set(cls.find(store=False, **attr_value_pairs))
        found_keys = set(entity.uid for entity in found)
        for key, value in attr_value_pairs.items():
            if not isinstance(value, Entity):
                raise TypeError(joins("relation value is not entity:", value))
            attr_value_pairs[key] = value.uid
        found.update(cls.find(cache=False, ignore_keys=found_keys,
                              **attr_value_pairs))
        return list(found)

    @classmethod
    def get(cls, key=None, default=None, cache=True, store=True,
            subclasses=True, **attr_value_pairs):
        """Get an entity by one or more of their attribute values.

        :param key: The key to get; if given `attr_value_pairs` will be ignored
        :param default: A default value to return if no entity is found; if
                        default is an exception, it will be raised instead
        :param bool cache: Whether to check the caches
        :param bool store: Whether to check the store
        :param bool subclasses: Whether to check subclasses as well
        :param iterable attr_value_pairs: Pairs of attributes and values to
                                          match against
        :returns Entity: A matching entity, or default
        :raises KeyError: If more than one entity matches the given values

        """
        if key is None:
            matches = cls.find(cache=cache, store=store,
                               subclasses=subclasses,
                               **attr_value_pairs)
            if len(matches) > 1:
                raise KeyError(joins("get returned more than one match:",
                                     matches, "using attrs", attr_value_pairs))
            if matches:
                return matches[0]
        else:
            if cache:
                if key in cls._instances:
                    return cls._instances[key]
            if subclasses:
                for subclass in cls.__subclasses__():
                    found = subclass.get(key, cache=cache, store=store)
                    if found:
                        return found
            if store:
                if cls._store.has(key):
                    return cls.reconstruct(cls._store.get(key))
        # Nothing was found.
        if isinstance(default, type) and issubclass(default, Exception):
            raise default
        else:
            return default

    @classmethod
    def all(cls):
        """Return all active instances of this entity.

        :returns list: All active instances of this entity type

        """
        return [instance for instance in cls._instances.values()
                if instance.active]

    def save(self):
        """Store this entity."""
        if not self.is_savable:
            log.warning("Tried to save non-savable entity %s!", self)
            return
        if "_old_key" in self.tags:
            # The entity's key has changed, so we need to handle that.
            old_key = self.tags["_old_key"]
            if self._store.has(old_key):
                self._store.delete(old_key)
            del self.tags["_old_key"]
        data = self.serialize()
        self._store.put(self.uid, data)
        self._dirty = False

    def revert(self):
        """Revert this entity to a previously saved state."""
        if not self._store:
            raise TypeError("cannot revert entity with no store")
        data = self._store.get(self.uid)
        if self.uid != data["uid"]:
            raise ValueError(joins("uid mismatch trying to revert", self))
        self.deserialize(data)
        self._dirty = False

    def clone(self):
        """Create a new entity with a copy of this entity's data.

        :returns Entity: The new, cloned entity

        """
        entity_class = type(self)
        data = self.serialize()
        del data["uid"]
        new_entity = entity_class(data)
        return new_entity

    def delete(self):
        """Delete this entity from the caches and its store."""
        for attr, cache in self._caches.items():
            attr_value = getattr(self, attr)
            if attr_value in cache:
                del cache[attr_value]
        if self._store and self._store.has(self.uid):
            self._store.delete(self.uid)
        if self.uid in self._instances:
            del self._instances[self.uid]


# We create a global EntityManager here for convenience, and while the
# server will generally only need one to work with, they are NOT singletons
# and you can make more EntityManager instances if you like.
ENTITIES = EntityManager()


@Entity.register_attr("version")
class EntityVersion(Attribute):

    """An entity's version."""

    default = 1

    @classmethod
    def validate(cls, entity, new_value):
        if not isinstance(new_value, int):
            raise TypeError("entity version must be a number")
        return new_value
