import abc

from cached_property import cached_property
import troposphere as ts


class resource(cached_property):
    """A cached property decorator that marks troposphere resources."""
    pass


class parameter(cached_property):
    """A cached property decorator that marks troposphere parameters."""
    pass


class ResourceGroupMeta(abc.ABCMeta):
    """Metaclass that registers the names of resource property attributes."""
    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        cls._resources = [name for name, attr in namespace.items() if isinstance(attr, resource)]
        cls._parameters = [name for name, attr in namespace.items() if isinstance(attr, parameter)]


class ResourceGroup(metaclass=ResourceGroupMeta):
    """Generates a json cloudformation template.
    
    """
    def __init__(self, config, *, prefix=''):
        self._config = config
        self._prefix = prefix

    def _get_logical_id(self, name):
        return '{}{}'.format(self._prefix, name)

    def get_template(self):
        t = ts.Template()
        self.add_to_template(t)
        return t.to_json()

    def add_to_template(self, t):
        for name in self._resources:
            t.add_resource(getattr(self, name))

        for name in self._parameters:
            t.add_parameter(getattr(self, name))


