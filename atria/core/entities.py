# -*- coding: utf-8 -*-
"""Entities, the base of all complex MUD objects."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2015 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from copy import deepcopy
from weakref import WeakValueDictionary

from .logs import get_logger
from .timing import TIMERS
from .utils.exceptions import AlreadyExists
from .utils.funcs import class_name, joins
from .utils.mixins import (HasFlags, HasFlagsMeta, HasTags,
                           HasWeaks, HasWeaksMeta)


log = get_logger("entities")


# noinspection PyDocstring
class _DataBlobMeta(HasWeaksMeta):

    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        cls._blobs = {}
        cls._attrs = {}

    def register_blob(cls, name):

        """Decorate a data blob to register it in this blob.

        :param str name: The name of the field to store the blob
        :returns: None
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
            cls._blobs[name] = blob_class
            setattr(cls, name, property(lambda s: s._blobs[name]))
            return blob_class

        return _inner

    def register_attr(cls, name):

        """Decorate an attribute to register it in this blob.

        :param str name: The name of the field to store the attribute
        :returns: None
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
            cls._attrs[name] = attr_class
            getter = lambda s: s._get_attr_val(name)
            setter = (lambda s, v: s._set_attr_val(name, v)
                      if not attr_class._read_only else None)
            setattr(cls, name, property(getter, setter))
            return attr_class

        return _inner


class DataBlob(HasWeaks, metaclass=_DataBlobMeta):

    """A collection of attributes and sub-blobs on an entity."""

    # These are overridden in the metaclass, I just put them here
    #  to avoid a lot of unresolved reference errors in IDE introspection
    _blobs = {}
    _attrs = {}

    def __init__(self, entity):
        super().__init__()
        self._entity = entity
        self._attr_values = {}
        for key, attr in self._attrs.items():
            # noinspection PyProtectedMember
            self._attr_values[key] = attr._default
        self._blobs = self._blobs.copy()
        for key, blob in self._blobs.items():
            self._blobs[key] = blob(entity)

    @property
    def _entity(self):
        return self._get_weak("entity")

    @_entity.setter
    def _entity(self, new_entity):
        self._set_weak("entity", new_entity)

    def _get_attr_val(self, name):
        return self._attr_values.get(name)

    # noinspection PyProtectedMember
    def _set_attr_val(self, name, value, validate=True):
        attr = self._attrs[name]
        old_value = self._attr_values.get(name)
        if validate:
            value = attr._validate(value)
        entity = self._entity
        if entity._base_blob == self and entity._store_key == name:
            # We're updating our store key, we need to check for an old one
            entity.tags["_old_key"] = old_value
        self._attr_values[name] = value
        entity.dirty()
        attr._changed(self, old_value, value)

    def _update(self, blob):
        """Merge this blob with another, replacing blobs and attrs.

        Sub-blobs and attrs on the given blob with take precedent over those
        existing on this blob.

        :param DataBlob blob: The blob to merge this blob with
        """
        self._blobs.update(blob._blobs)
        self._attrs.update(blob._attrs)
        self._attr_values.update(blob._attr_values)

    def serialize(self):
        """Create a dict from this blob, sanitized and suitable for storage.

        All sub-blobs will in turn be serialized.

        :returns dict: The serialized data

        """
        data = {}
        for key, blob in self._blobs.items():
            data[key] = blob.serialize()
        for key, attr in self._attrs.items():
            if key in data:
                raise KeyError(joins("duplicate blob key:", key))
            value = self._attr_values.get(key)
            # noinspection PyProtectedMember
            data[key] = attr._serialize(value)
        return data

    def deserialize(self, data):
        """Update this blob's data using values from a dict.

        All sub-blobs found will in turn be deserialized.

        :param dict data: The data to deserialize
        :returns: None

        """
        for key, value in data.items():
            if key in self._attrs:
                # noinspection PyProtectedMember
                value = self._attrs[key]._deserialize(value)
                self._set_attr_val(key, value, validate=False)
            elif key in self._blobs:
                self._blobs[key].deserialize(value)
            else:
                log.warn(joins("Unused data while deserializing ",
                               class_name(self), ": '", key, "':'",
                               value, "'", sep=""))


class _UnsetMeta(type):

    def __bool__(cls):
        return False


class Unset(metaclass=_UnsetMeta):

    """A unique value to note that an attribute hasn't been set."""

    pass


class Attribute:

    """A single attribute of an entity.

    These are templates for the behavior of an attribute, they will not be
    instantiated and as such have no instance-based variables.

    The value of `_default` should not be set to a mutable type, as it will
    be passed by reference to all instantiated blobs and risks being changed
    elsewhere in the code.

    """

    _default = Unset  # Do NOT use mutable types for this.
    _read_only = False

    @classmethod
    def _validate(cls, new_value):
        """Validate a value for this attribute.

        This will be called by the blob when setting the value for this
        attribute, override it to perform any checks or sanitation. This
        should either return a valid value for the attribute or raise an
        exception as to why the value is invalid.

        :param new_value: The potential value to validate
        :returns: The validated (and optionally sanitized) value

        """
        return new_value

    @classmethod
    def _changed(cls, blob, old_value, new_value):
        """Perform any actions necessary after this attribute's value changes.

        This will be called by the blob after the value of this attribute
        has changed, override it to do any necessary post-setter actions.

        :param DataBlob blob: The blob that changed
        :param old_value: The previous value
        :param new_value: The new value
        :returns: None

        """
        pass

    @classmethod
    def _serialize(cls, value):
        """Serialize a value for this attribute that is suitable for storage.

        This will be called by the blob when serializing itself, override it
        to perform any necessary conversion or sanitation.

        :param value: The value to serialize
        :returns: The serialized value

        """
        return value

    @classmethod
    def _deserialize(cls, value):
        """Deserialize a value for this attribute from storage.

        This will be called by the blob when deserializing itself, override it
        to perform any necessary conversion or sanitation.

        :param value: The value to deserialize
        :returns: The deserialized value

        """
        return value


# noinspection PyDocstring
class _EntityMeta(HasFlagsMeta, HasWeaksMeta):

    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        cls._base_blob = type(name + "BaseBlob", (DataBlob,), {})
        cls._instances = WeakValueDictionary()

    def register_blob(cls, name):
        """Decorate a data blob to register it on this entity.

        :param str name: The name of the field to store the blob
        :returns: None
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
        :returns: None
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


class EntityManager:

    """A manager for entity types."""

    def __init__(self):
        """Create a new entity manager."""
        self._entities = {}

    def __contains__(self, entity):
        return entity in self._entities

    def __getitem__(self, entity):
        return self._entities[entity]

    def register(self, entity):
        """Register an entity type.

        This method can be used to decorate an Entity class.

        :param Entity entity: The entity to be registered
        :returns Entity: The registered entity
        :raises AlreadyExists: If an entity with that class name already exists
        :raises KeyError: If an entity with the same _uid_code attribute
                          already exists
        :raises TypeError: If the supplied or decorated class is not a
                           subclass of Entity.

        """
        if (not isinstance(entity, type) or
                not issubclass(entity, Entity)):
            raise TypeError("must be subclass of Entity to register")
        name = entity.__name__
        if name in self._entities:
            raise AlreadyExists(name, self._entities[name], entity)
        for registered_entity in self._entities.values():
            # noinspection PyProtectedMember,PyUnresolvedReferences
            if entity._uid_code == registered_entity._uid_code:
                raise KeyError("cannot register two Entity classes with the"
                               " same UID code")
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
            log.info("Saved %s dirty entities.", count)


class Entity(HasFlags, HasTags, HasWeaks, metaclass=_EntityMeta):

    """The base of all persistent objects in the game."""

    _store = None
    _store_key = "uid"
    _uid_code = "E"
    _uid_history = {}  # Don't redefine on subclasses

    # noinspection PyProtectedMember
    def __init__(self, data=None):
        super().__init__()
        parent = super(self.__class__, self)
        if hasattr(parent, "_base_blob"):
            self._base_blob = parent._base_blob(self)
            # noinspection PyUnresolvedReferences
            self._base_blob._update(self.__class__._base_blob(self))
        else:
            self._base_blob = self._base_blob(self)
        self._dirty = False
        self._savable = True
        # Never, ever manually change an object's UID! There are no checks
        # for removing the old UID from the store, updating UID links, or
        # anything else like that. Bad things will happen!
        self._uid = None
        if data is not None:
            self.deserialize(data)
        if self._uid is None:
            self._uid = self.make_uid()
        # noinspection PyUnresolvedReferences
        self._instances[self._uid] = self

    def __repr__(self):
        return joins("Entity<", self.uid, ">", sep="")

    @property
    def uid(self):
        """Return this entity's UID."""
        return self._uid

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
        data["uid"] = self._uid
        data["flags"] = self.flags.as_tuple
        data["tags"] = deepcopy(self.tags.as_dict)
        return data

    def deserialize(self, data):
        """Update this entity's data using values from a dict.

        :param dict data: The data to deserialize
        :returns: None

        """
        if "uid" in data:
            self._uid = data["uid"]
            del data["uid"]
        if "flags" in data:
            self.flags.add(*data["flags"])
            del data["flags"]
        if "tags" in data:
            self.tags.clear()
            self.tags.update(data["tags"])
            del data["tags"]
        self._base_blob.deserialize(data)

    @classmethod
    def make_uid(cls):
        """Create a UID for this entity.

        UIDs are in the form "X-YYYYYY-Z", where X is the entity code, Y is
        the current time code, and Z is the number of UIDs created during
        the same time code. (Ex. "E-ngfazj-0")

        If my base 36 math is to be believed, the time codes should remain
        six digits until December 23rd 2038, and after that will remain
        seven digits until the year 4453.

        :returns str: The new UID

        """
        time_code = TIMERS.get_time_code()
        last_time, last_count = cls._uid_history.get(cls._uid_code, (0, 0))
        if time_code == last_time:
            last_count += 1
        else:
            last_time = time_code
            last_count = 0
        uid = "-".join((cls._uid_code, time_code, str(last_count)))
        cls._uid_history[cls._uid_code] = (last_time, last_count)
        return uid

    # noinspection PyProtectedMember,PyUnresolvedReferences
    @classmethod
    def exists(cls, key):
        """Check if an entity with the given key exists.

        :param key: The key the entity's data is stored under
        :returns bool: True if it exists, else False

        """
        # Check the store first
        if cls._store and cls._store.has(key):
            return True
        # Then check unsaved instances
        if cls._store_key == "uid":
            if key in cls._instances:
                return True
        else:
            # This entity isn't saved by UID, so we have to check
            # each one for a matching store key.
            for entity in cls._instances.values():
                if getattr(entity, cls._store_key) == key:
                    return True
        return False

    # noinspection PyProtectedMember,PyUnresolvedReferences
    @classmethod
    def find(cls, attr, value, store_only=False, cache_only=False):
        """Find one or more entities by one of their attribute values.

        :param str attr: The name of the attribute to match against
        :param value: The matching attribute value
        :param bool store_only: Whether to only check the store
        :param bool cache_only: Whether to only check the _instances cache
        :returns list: A list of found entities, if any
        :raises ValueError: If both `store_only` and `cache_only` are True

        """
        if store_only and cache_only:
            raise ValueError("cannot check both store only and cache only")
        found = []
        if not cache_only:
            for key in cls._store.keys():
                data = cls._store.get(key)
                if data:
                    if data.get(attr) == value:
                        entity = cls(data)
                        found.append(entity)
        if not store_only:
            for entity in cls._instances.values():
                if entity not in found and getattr(entity, attr) == value:
                    found.append(entity)
        return found

    # noinspection PyProtectedMember,PyUnresolvedReferences
    @classmethod
    def load(cls, key, from_cache=True):
        """Load an entity from storage.

        If `from_cache` is True and an instance is found in the _instances
        cache then the found instance will be returned as-is and NOT
        reloaded from the store. If you want to reset an entity's data to a
        stored state, use the revert method instead.

        :param key: The key the entity's data is stored under
        :param bool from_cache: Whether to check the _instances cache for a
                                match before reading from storage
        :returns Entity: The loaded entity
        :raises KeyError: If the given key is not found in the store

        """
        if from_cache:
            if cls._store_key == "uid":
                if key in cls._instances:
                    return cls._instances[key]
            else:
                for entity in cls._instances.values():
                    if getattr(entity, cls._store_key) == key:
                        return entity
        if cls._store:
            data = cls._store.get(key)
            if data:
                if "uid" not in data:
                    log.warn("No uid for %s loaded with key: %s",
                             class_name(cls), key)
                entity = cls(data)
                return entity
        raise KeyError(joins("couldn't load", class_name(cls),
                       "with key:", key))

    def save(self):
        """Store this entity."""
        if not self.is_savable:
            log.warn("Tried to save non-savable entity %s", self)
            return
        old_key = self.tags.get("_old_key")
        if old_key:
            if self._store.has(old_key):
                self._store.delete(old_key)
            del self.tags["_old_key"]
        data = self.serialize()
        key = data[self._store_key]
        self._store.put(key, data)
        self._dirty = False

    def revert(self):
        """Revert this entity to a previously saved state."""
        if not self._store:
            raise TypeError("cannot revert entity with no store")
        key = getattr(self, self._store_key)
        data = self._store.get(key)
        if self.uid != data["uid"]:
            raise ValueError(joins("uid mismatch trying to revert", self))
        self.deserialize(data)

    def clone(self, new_key):
        """Create a new entity with a copy of this entity's data.

        :param new_key: The key the new entity will be stored under;
                        new_key can be callable, in which case the return
                        value will be used as the key

        """
        if not self._store:
            raise TypeError("cannot clone entity with no store")
        entity_class = type(self)
        if callable(new_key):
            new_key = new_key()
        if self._store.has(new_key):
            raise KeyError(joins("key exists in entity store:", new_key))
        data = self.serialize()
        del data["uid"]
        new_entity = entity_class(data)
        setattr(new_entity, self._store_key, new_key)
        return new_entity


# We create a global EntityManager here for convenience, and while the
# server will generally only need one to work with, they are NOT singletons
# and you can make more EntityManager instances if you like.
ENTITIES = EntityManager()


@Entity.register_attr("version")
class EntityVersion(Attribute):

    """An entity's version."""

    _default = 1

    @classmethod
    def _validate(cls, value):
        if not isinstance(value, int):
            raise TypeError("entity version must be a number")
        return value
