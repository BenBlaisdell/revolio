import abc
import functools

from revolio.serializable import Serializable
from revolio.serializable.fields import Field


def validate(**fields):
    for field in fields.values():
        assert isinstance(field, Field)

    Request = type(
        'Request',
        (Serializable,),
        fields,
    )

    def decorator(func):
        @functools.wraps(func)
        def wrapper(f, request):
            return func(f, Request.deserialize(request))

        return wrapper

    return decorator


class Function(metaclass=abc.ABCMeta):

    def __init__(self, ctx):
        super().__init__()
        self._ctx = ctx

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

    @property
    def url_prefix(self):
        return f'/api/{self.api_version}'

    @property
    def api_version(self):
        return self._ctx.config['Web']['Version']

    @property
    def url_path(self):
        return f'{self.url_prefix}/call/{type(self).__name__}'

    @property
    def external_url(self):
        host = self._ctx.config['Web']['External']['RecordSetName']
        return f'http://{host}{self.url_path}'

    @property
    def internal_url(self):
        return 'http://{host}{path}'.format(
            host=self._ctx.config['Web']['Internal']['RecordSetName'],
            path=self.url_path,
        )
