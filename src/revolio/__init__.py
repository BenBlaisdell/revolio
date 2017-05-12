import inspect


class Inject:

    def __init__(self, callable):
        self._callable = callable

    def __get__(self, instance, owner):
        try:
            params = inspect.signature(self._callable).parameters.values()
            return self._callable(**{
                param.name: getattr(instance, param.name)
                for param in params
            })
        except Exception as e:
            raise Exception('Failed to inject dependencies for {}: {}'.format(str(self._callable), str(e))) from e


def inject(func):
    return Inject(func)
