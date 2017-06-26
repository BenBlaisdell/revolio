import abc
import datetime as dt
import enum

import revolio as rv
from revolio.serializable.serializable import Serializable, KeyFormat, _format_key

# constant to differentiate between None
NULL = object()


class Field:
    """
    
    Fields are python descriptors: https://docs.python.org/2/howto/descriptor.html
    See `__get__` and `__set__` methods.
    """

    @property
    def name(self):
        return self._name

    @property
    def names(self):
        return self._names

    @property
    def optional(self):
        return self._optional

    def __init__(self, optional=False, get_default=None, default=None, help=None):
        """
        
        Args:
            get_default (callable): A callable that returns a default value for the field or None if the field is required.
            help (str): A description of the field to use in documentation.
        """
        super().__init__()

        self._optional = optional
        self._get_default_value = get_default if (get_default is not None) else lambda: default
        self._help = help

    def __set_name__(self, owner, name):
        """
        
        https://www.python.org/dev/peps/pep-0487/
        """
        self._name = name

        self._names = {
            KeyFormat.Snake: name,
            KeyFormat.Camel: _format_key(name, from_f=KeyFormat.Snake, to_f=KeyFormat.Camel),
        }

        # register this field in the new serializable class
        rv.serializable.serializable.register_field(owner, self)

    def get_default_value(self):
        """Generate a default deserialized value for this field."""
        if not self._optional:
            raise Exception(f'Field "{self.name}" is required')

        return self._get_default_value()

    def validate(self, value):
        """Validate a deserialized value and raise an exception on failure."""
        raise NotImplementedError()

    def serialize(self, value, *, key_format=KeyFormat.Camel):
        """Serialize a deserialized value.
        
        Args:
            value: The object to serialize. This is assumed to be a valid value for this field.
            key_format: The format of the serialized field keys.
        """
        return value

    def deserialize(self, value, key_format):
        """Deserialize a serialized value.
        
        Args:
            value: The serialized data to deserialize. This could be an 
            key_format (KeyFormat): The format of the field keys in the serialized data.
        """
        return value

    def __get__(self, instance, owner):
        """Get the deserialized value from the instance.
        
        Getter method 
        
        Args:
            instance (Serializable): The instance through which this field is being accessed.
            owner (type): The class through which this field is being accessed.
        """
        # access through class
        if instance is None:
            return self

        try:
            return instance.__dict__[self]
        except Exception as e:
            raise AttributeError from e

    def __set__(self, instance, value):
        """Set the new deserialized value on the instance.
        
        Args:
            instance (Serializable): The instance whose field is being set.
            value: The deserialized value to set for this field.
        """
        if value is None:
            if not self.optional:
                raise Exception(f'Field "{self.name}" is not optional')
        else:
            try:
                self.validate(value)
            except Exception as e:
                raise Exception(f'Field "{self.name}" failed validation.') from e

        instance.__dict__[self] = value


class Int(Field):

    def __init__(self, *, min=None, max=None, **kwargs):
        super().__init__(**kwargs)
        self._min = min
        self._max = max

    def validate(self, value):
        assert isinstance(value, int)

        if self._min is not None:
            assert value >= self._min

        if self._max is not None:
            assert value <= self._max


class DateTime(Field):

    def __init__(self, format='%Y-%m-%d %H:%M:%S', **kwargs):
        super().__init__(**kwargs)
        self._format = format

    def validate(self, value):
        assert isinstance(value, dt.datetime)

    def serialize(self, value, **kwargs):
        return value.strftime(self._format)

    def deserialize(self, value, **kwargs):
        return dt.datetime.strptime(value, self._format)



class Str(Field):

    def validate(self, value):
        assert isinstance(value, str)


class Bool(Field):

    def validate(self, value):
        assert isinstance(value, bool)


class Enum(Field):

    def __init__(self, enum, **kwargs):
        """
        
        Args:
            enum (enum.Enum): The enum whose members to use as options.
        """
        super().__init__(**kwargs)
        self._enum = enum

    def validate(self, value):
        assert value in self._enum

    def serialize(self, value, **kwargs):
        return value.name

    def deserialize(self, value, key_format):
        return self._enum[value]


class Dict(Field):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def validate(self, value):
        assert isinstance(value, dict)


class Nested(Field):

    def __init__(self, cls, **kwargs):
        super().__init__(**kwargs)
        assert issubclass(cls, Serializable)
        self._cls = cls

    def validate(self, value):
        assert isinstance(value, self._cls)

    def serialize(self, value, **kwargs):
        return value.serialize()

    def deserialize(self, value, key_format):
        return self._cls.deserialize(value, key_format=key_format)


class ObjectEnum(Field):

    # todo: implicit nested schema for docs

    def __init__(self, s_enum, type_field='type', params_field='parameters', **kwargs):
        """A field that accepts any instance of an enum of serializable objects.
        
        This field is serialized as a dict with two fields:
        1) A `type` enum field that holds the name of the enum member corresponding to the serialized object.
        2) A `parameters` dict field that holds the parameters of the serialized object.
        
        The names of both fields can be overwritten, but must be defined in snake case.
    
        Args:
            s_enum (enum.EnumMeta): The enum of Serializable classes that can be passed.
            type_name (str): The name of the `type` field.
            params_field (str): The name of the `parameters` field.
        """
        super().__init__(**kwargs)

        assert issubclass(s_enum, enum.Enum)
        # todo: assert serializable
        self._enum = s_enum

        assert isinstance(type_field, str)
        # todo: assert snake case
        self._type_field = type_field

        assert isinstance(params_field, str)
        # todo: assert snake case
        self._params_field = params_field

    def validate(self, value):
        # todo: assert base type
        assert type(value) in [m.value for m in self._enum]

    def serialize(self, value, *, key_format=KeyFormat.Snake, **kwargs):
        return {
            self._type_field: {m.value: m.name for m in self._enum}[type(value)],
            self._params_field: value.serialize(key_format=key_format),
        }

    def deserialize(self, value, key_format):
        type_name = value[_format_key(self._type_field, from_f=KeyFormat.Snake, to_f=key_format)]
        parameters = value[_format_key(self._params_field, from_f=KeyFormat.Snake, to_f=key_format)]

        serializable_cls = {m.name: m.value for m in self._enum}[type_name]
        return serializable_cls.deserialize(parameters, key_format=key_format)
