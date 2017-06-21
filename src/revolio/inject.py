import functools
import inspect

import cached_property


class Inject(cached_property.threaded_cached_property):

    def __init__(self, callable):

        @functools.wraps(callable)
        def wrapper(ctx):
            return _init_injected(ctx, callable)

        super(Inject, self).__init__(wrapper)


def _init_injected(ctx, injected):
    try:
        params = inspect.signature(injected).parameters.values()
        return injected(**{
            param.name: getattr(ctx, param.name)
            for param in params
        })
    except Exception as e:
        raise Exception(f'Failed to inject dependencies for {injected}') from e
