# -*- coding: utf-8 -*-
"""Entities, the base of all complex MUD objects."""
# Part of Atria MUD Server (https://github.com/whutch/atria)
# :copyright: (c) 2008 - 2014 Will Hutcheson
# :license: MIT (https://github.com/whutch/atria/blob/master/LICENSE.txt)

from weakref import WeakValueDictionary

from .logs import get_logger
from .timing import TIMERS
from .utils.exceptions import AlreadyExists
from .utils.funcs import class_name, joins


log = get_logger("entities")


# noinspection PyDocstring
class _DataBlobMeta(type):

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


class DataBlob(metaclass=_DataBlobMeta):

    """A collection of attributes and sub-blobs on an entity."""

    # These are overridden in the metaclass, I just put them here
    #  to avoid a lot of unresolved reference errors in IDE introspection
    _blobs = {}
    _attrs = {}

    def __init__(self):
        self._attr_values = {}
        for key, attr in self._attrs.items():
            # noinspection PyProtectedMember
            self._attr_values[key] = attr._default
        self._blobs = self._blobs.copy()
        for key, blob in self._blobs.items():
            self._blobs[key] = blob()

    def _get_attr_val(self, name):
        return self._attr_values.get(name)

    def _set_attr_val(self, name, value):
        attr = self._attrs[name]
        # noinspection PyProtectedMember
        self._attr_values[name] = attr._validate(value)

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
                self._set_attr_val(key, value)
            elif key in self._blobs:
                self._blobs[key].deserialize(value)
            else:
                log.warn(joins("Unused data while deserializing ",
                               class_name(self), ": '", key, "':'",
                               value, "'", sep=""))


class Attribute:

    """A single attribute of an entity.

    These are templates for the behavior of an attribute, they will not be
    instantiated and as such have no instance-based variables.

    The value of `_default` should not be set to a mutable type, as it will
    be passed by reference to all instantiated blobs and risks being changed
    elsewhere in the code.

    """

    _default = None  # Do NOT use mutable types for this
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
class _EntityMeta(type):

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


class Entity(metaclass=_EntityMeta):

    """The base of all persistent objects in the game."""

    _store = None
    _store_key = "uid"
    _uid_code = "E"
    _uid_history = {}  # Don't redefine on subclasses

    # noinspection PyProtectedMember
    def __init__(self, data=None):
        parent = super(self.__class__, self)
        if hasattr(parent, "_base_blob"):
            self._base_blob = parent._base_blob()
            # noinspection PyUnresolvedReferences
            self._base_blob._update(self.__class__._base_blob())
        else:
            self._base_blob = self._base_blob()
        self._uid = None
        if data is not None:
            self.deserialize(data)
        if self._uid is None:
            self._uid = self.make_uid()
        # noinspection PyUnresolvedReferences
        self._instances[self._uid] = self

    @property
    def uid(self):
        """Return the entity's UID."""
        return self._uid

    def serialize(self):
        """Create a sanitized dict from the data on this entity.

        :returns dict: The serialized data

        """
        data = self._base_blob.serialize()
        data["uid"] = self._uid
        return data

    def deserialize(self, data):
        """Update this entity's data using values from a dict.

        :param dict data: The data to deserialize
        :returns: None

        """
        if "uid" in data:
            self._uid = data["uid"]
            del data["uid"]
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
        if not self._store:
            raise TypeError("cannot save entity with no store")
        data = self.serialize()
        key = data[self._store_key]
        self._store.put(key, data)

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


@Entity.register_attr("version")
class EntityVersion(Attribute):

    """An entity's version."""

    _default = 1

    @classmethod
    def _validate(cls, value):
        if not isinstance(value, int):
            raise TypeError("entity version must be a number")
        return value
