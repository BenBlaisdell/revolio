import abc
import collections
import copy
import logging
import uuid

import boto3
from cached_property import cached_property
import troposphere as ts


_log = logging.getLogger(__name__)


class resource(cached_property):
    """A cached property decorator that marks troposphere resources."""

    def __get__(self, obj, cls):
        r = super().__get__(obj, cls)
        for a in self._actions:
            a.link(r)

        return r

    @cached_property
    def _actions(self):
        return []

    def action(self, func):
        a = ResourceAction(func)
        self._actions.append(a)
        return a


class ResourceAction:

    def __init__(self, func):
        super().__init__()
        self._func = func
        self._resource = None
        self._success = False

    def link(self, resource):
        if self._resource is not None:
            raise Exception('ResourceAction is already linked to a resource')

        self._resource = resource

    def execute(self):
        if self._success:
            raise Exception('Already executed ResourceAction')

        self._success = self._func()
        return self._success

    def ping_resource(self, stack_name):
        boto3.client('cloudformation').signal_resource(
            Status='SUCCESS',
            StackName=stack_name,
            LogicalResourceId=self._resource.title,
            UniqueId='{resource}-{uuid}'.format(
                resource=self._resource.title,
                uuid=str(uuid.uuid4()),
            ),
        )


class parameter(cached_property):
    """A cached property decorator that marks troposphere parameters."""

    def __init__(self, func):
        super().__init__(func)
        self._value = None

    def __get__(self, obj, cls):
        p = super().__get__(obj, cls)
        self._value.link(p)
        return p

    def value(self, func):
        v = ParameterValue(func)
        self._value = v
        return v


class ParameterValue:

    def __init__(self, func):
        super().__init__()
        self._func = func
        self._parameter = None

    def link(self, parameter):
        if self._parameter is not None:
            raise Exception('ParameterValue is already linked to a resource')

        self._parameter = parameter

    def get_item(self, group):
        return self._parameter.title, self._func(group)


class resource_group(cached_property):
    """A cached property decorator that marks sub ResourceGroups."""
    pass


class ResourceGroupMeta(abc.ABCMeta):
    """Metaclass that registers the names of resource property attributes."""
    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        cls._resources = [name for name, attr in namespace.items() if isinstance(attr, resource)]
        cls._parameters = [name for name, attr in namespace.items() if isinstance(attr, parameter)]
        cls._resource_groups = [name for name, attr in namespace.items() if isinstance(attr, resource_group)]
        cls._resource_actions = [name for name, attr in namespace.items() if isinstance(attr, ResourceAction)]
        cls._parameter_values = [name for name, attr in namespace.items() if isinstance(attr, ParameterValue)]


class ResourceGroup(metaclass=ResourceGroupMeta):
    """Generates a json cloudformation template.
    
    """
    def __init__(self, ctx, config, *, prefix=''):
        self._ctx = ctx
        self._config = config
        self._prefix = prefix
        self._remaining_actions = copy.copy(self._resource_actions)

    @property
    def config(self):
        return self._config

    def _get_logical_id(self, name):
        return f'{self._prefix}{name}'

    def get_template(self):
        t = ts.Template()
        self.add_to_template(t)
        return t.to_json()

    def add_to_template(self, t):
        for name in self._resources:
            t.add_resource(getattr(self, name))

        for name in self._parameters:
            t.add_parameter(getattr(self, name))

        for name in self._resource_groups:
            getattr(self, name).add_to_template(t)

    def execute_actions(self):
        self._remaining_actions = filter(self._execute_action, self._remaining_actions)
        for name in self._resource_groups:
            getattr(self, name).execute_actions()

    def _execute_action(self, name):
        _log.info('Trying to execute action: {}'.format(name))
        a = getattr(self, name)
        success = a.execute()

        if success:
            _log.info(f'Successfully executed action: {name}')
            a.ping_resource(self._ctx.stack_name)

        return False

    def get_parameters(self):
        others = [getattr(self, n).get_parameters() for n in self._resource_groups]
        return dict(collections.ChainMap(
            dict(p.get_item(self) for p in map(lambda n: getattr(self, n), self._parameter_values)),
            *others
        ))
