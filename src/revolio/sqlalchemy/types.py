import enum
import re

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql

from revolio.serializable import Serializable, KeyFormat
from revolio.serializable.fields import ObjectEnum
from revolio.serializable.serializable import format_key


class Regex(sa.types.TypeDecorator):
    impl = sa.String

    def process_bind_param(self, value, dialect):
        if value is None:
            return None

        if isinstance(value, str):
            return value

        # assume type regex
        return value.pattern

    def process_result_value(self, value, dialect):
        if value is None:
            return None

        return re.compile(value)


def serializable(cls):
    assert issubclass(cls, Serializable)

    class SerializableType(sa.types.TypeDecorator):
        impl = sa.dialects.postgresql.JSONB

        def process_bind_param(self, value, dialect):
            if value is None:
                return None

            assert isinstance(value, cls)
            return value.serialize(key_format=KeyFormat.Snake) if (value is not None) else None

        def process_result_value(self, value, dialect):
            if value is None:
                return None

            return cls.deserialize(value, key_format=KeyFormat.Snake) if (value is not None) else None

    SerializableType.__name__ = '{}Type'.format(cls.__name__)
    return SerializableType


def serializable_enum(enum_cls, type_field='type', params_field='parameters'):
    assert issubclass(enum_cls, enum.Enum)
    field = ObjectEnum(enum_cls, type_field=type_field, params_field=params_field)

    class SerializableEnumType(sa.types.TypeDecorator):
        impl = sa.dialects.postgresql.JSONB

        def process_bind_param(self, value, dialect):
            return field.serialize(value) if (value is not None) else None

        def process_result_value(self, value, dialect):
            return field.deserialize(value, KeyFormat.Snake) if (value is not None) else None

    SerializableEnumType.__name__ = '{}Type'.format(enum_cls.__name__)
    return SerializableEnumType
