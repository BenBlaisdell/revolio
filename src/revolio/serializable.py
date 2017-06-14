import abc
import collections
import enum

import revolio as rv
import revolio.util


class KeyFormat(enum.Enum):
    """Functions to transform keys to desired format."""
    Camel = 'Camel'
    Snake = 'Snake'


class Serializable(metaclass=abc.ABCMeta):

    def serialize(self, *, key_format=KeyFormat.Camel):
        assert isinstance(key_format, KeyFormat)
        data = self._serialize()

        if key_format is KeyFormat.Camel:
            return data
        if key_format is KeyFormat.Snake:
            return _transform_keys(data, rv.util.camel_to_snake)

    @abc.abstractmethod
    def _serialize(self):
        pass

    @classmethod
    def deserialize(cls, data, *, key_format=KeyFormat.Camel):
        if data is None:
            return None

        assert isinstance(key_format, KeyFormat)

        if key_format is KeyFormat.Camel:
            pass
        if key_format is KeyFormat.Snake:
            data = _transform_keys(data, rv.util.snake_to_camel)

        return cls._deserialize(data)

    @staticmethod
    @abc.abstractmethod
    def _deserialize(data):
        pass


def _transform_keys(dct, func):
    return {
        func(k): _transform_keys(v, func) if isinstance(v, collections.Mapping) else v
        for k, v in dct.items()
    }
