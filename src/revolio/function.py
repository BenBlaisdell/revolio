import abc
import collections


class Function(metaclass=abc.ABCMeta):

    def __init__(self):
        super().__init__()

    @property
    def name(self):
        return type(self).__name__

    @abc.abstractmethod
    def format_request(self, *args, **kwargs):
        return {}

    @abc.abstractmethod
    def handle_request(self, request):
        return {
            'Message': self(),
        }

    @abc.abstractmethod
    def __call__(self, *args, **kwargs):
        return 'Success'
