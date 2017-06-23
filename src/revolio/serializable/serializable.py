import collections
import enum

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql
import sqlalchemy.ext.mutable

import revolio as rv
import revolio.util.str


class KeyFormat(enum.Enum):
    """Functions to transform keys to desired format."""
    Camel = 'Camel'
    Snake = 'Snake'


_key_transformations = {
    (KeyFormat.Camel, KeyFormat.Snake): rv.util.str.camel_to_snake,
    (KeyFormat.Snake, KeyFormat.Camel): rv.util.str.snake_to_camel,
}


def _format_key(key, from_f, to_f):
    """Transform a key from one format to another.
    
    Args:
        key (str): The key to format.
        from_f (KeyFormat): The current format of the key.
        to_f (KeyFormat): The desired format of the key.
    """
    # no change desired
    if from_f is to_f:
        return key

    transformation = (from_f, to_f)
    if transformation not in _key_transformations:
        raise Exception('Unknown key transformation ')

    return _key_transformations[transformation](key)


def column_type(cls):
    assert issubclass(cls, Serializable)

    class SerializableType(sa.types.TypeDecorator):
        impl = sa.dialects.postgresql.JSONB

        def process_bind_param(self, value, dialect):
            assert isinstance(value, cls)
            return value.serialize(key_format=KeyFormat.Snake) if (value is not None) else None

        def process_result_value(self, value, dialect):
            return cls.deserialize(value, key_format=KeyFormat.Snake) if (value is not None) else None

    SerializableType.__name__ = '{}Type'.format(cls.__name__)
    return SerializableType


# _directory[DummySerializable][KeyFormat.Camel]['DummyField'] = fields.Field()
# direct fields are added first through the __add_name__ hook on the field
# inherited fields are added through the __init_subclass__ hook on the serializable
_directory = collections.defaultdict(lambda: collections.defaultdict(dict))


def register_field(s_cls, field):
    if s_cls not in _directory:
        _directory[s_cls] = {key_format: {} for key_format in KeyFormat}

    for key_format in KeyFormat:
        _directory[s_cls][key_format][field.names[key_format]] = field


class Serializable:
    """A serializable object with a built-in schema.
    
    """

    def __init__(self, **kwargs):
        """
        
        Args:
            **kwargs: Deserialized attributes with which to initialize the serializable. Missing values are defaulted.
        """
        super().__init__()

        self._check_extra_fields(kwargs, KeyFormat.Snake)

        for name, field in _directory[type(self)][KeyFormat.Snake].items():
            value = kwargs[name] if name in kwargs else field.get_default_value()

            if value is not None:
                try:
                    field.validate(value)
                except:
                    raise Exception(f'Field "{name}" failed validation')

            self.__dict__[field] = value

    def __init_subclass__(cls):
        """Add parent fields to the new class's fields registry.
        
        https://www.python.org/dev/peps/pep-0487/
        """
        super().__init_subclass__()

        serializable_bases = filter(lambda b: issubclass(b, Serializable), cls.__bases__)
        for base in serializable_bases:
            for field in _directory[base][KeyFormat.Snake].values():
                register_field(cls, field)

    def serialize(self, *, key_format=KeyFormat.Camel):
        """
        
        Args:
            key_format (KeyFormat): The output format of field keys.
        """
        assert isinstance(key_format, KeyFormat)
        return {
            key: _get_serialized_value(self, field, key_format)
            for key, field in _directory[type(self)][key_format].items()
        }

    @classmethod
    def deserialize(cls, data, *, key_format=KeyFormat.Camel):
        """Deserialize the data into an instance of this serializable.
        
        Missing keys in the data are defaulted if not required.
        
        Args:
            data (Collections.Mapping): The data to deserialize.
            key_format (KeyFormat): The format of field keys in the serialized data.
        """
        if not isinstance(data, collections.Mapping):
            raise Exception('Object to deserialize must be a mapping')

        cls._check_extra_fields(data, key_format)

        return cls(**{
            field.name: field.deserialize(value=data[key], key_format=key_format)
            for key, field in _directory[cls][key_format].items()
            if (key in data) and (data[key] is not None)
        })

    @classmethod
    def _check_extra_fields(cls, data, key_format):
        """Assert all fields in data are expected."""
        for key in data:
            if key not in _directory[cls][key_format]:
                raise Exception(f'Unknown key {key}')


def _get_serialized_value(obj, field, key_format):
    value = obj.__dict__[field]
    return field.serialize(value, key_format=key_format) if (value is not None) else None
