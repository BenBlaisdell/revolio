import enum
import functools
import inspect

import cached_property

import werkzeug.utils

werkzeug.utils.cached_property


class Scope(enum.Enum):
    Global = 'Global'


class Inject(cached_property.threaded_cached_property):

    def __init__(self, callable):

        @functools.wraps(callable)
        def wrapper(ctx):
            return _init_injected(ctx, callable)

        super(Inject, self).__init__(wrapper)


def _init_injected(ctx, callable):
    try:
        params = inspect.signature(callable).parameters.values()
        return callable(**{
            param.name: getattr(ctx, param.name)
            for param in params
        })
    except Exception as e:
        raise Exception('Failed to inject dependencies for {}: {}'.format(str(callable), str(e))) from e
