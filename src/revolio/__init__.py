import enum
import inspect

from werkzeug.utils import cached_property


class Scope(enum.Enum):
    Global = 'Global'


class Inject(cached_property):

    def __init__(self, callable):
        super(Inject, self).__init__(lambda ctx: _init_injected(ctx, callable))


def _init_injected(ctx, callable):
    try:
        params = inspect.signature(callable).parameters.values()
        return callable(**{
            param.name: getattr(ctx, param.name)
            for param in params
        })
    except Exception as e:
        raise Exception('Failed to inject dependencies for {}: {}'.format(str(callable), str(e))) from e
