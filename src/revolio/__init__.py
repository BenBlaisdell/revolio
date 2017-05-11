import inspect


class Inject:

    def __init__(self, callable):
        self._callable = callable

    def __get__(self, instance, owner):
        params = inspect.signature(self._callable).parameters.values()
        return self._callable(**{
            param.name: getattr(instance, param.name)
            for param in params
        })


def inject(func):
    return Inject(func)
