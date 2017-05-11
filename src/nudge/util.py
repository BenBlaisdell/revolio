import functools
import abc
import re


class AbstractMethodNotImplementedError(NotImplementedError):
    def __init__(self):
        super(AbstractMethodNotImplementedError, self).__init__()


class Serializable(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def serialize(self):
        raise AbstractMethodNotImplementedError()

    @classmethod
    @abc.abstractmethod
    def deserialize(cls, data):
        raise AbstractMethodNotImplementedError()


first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')


def camel_to_snake(name):
    s1 = first_cap_re.sub(r'\1_\2', name)
    return all_cap_re.sub(r'\1_\2', s1).lower()


def success_response():
    return {'Message': 'Success'}