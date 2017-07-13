import enum

import revolio as rv
import revolio.architecture.resources.ecr
import revolio.manager.context

from iris.core.context import IrisContext
from iris.infrastructure.resources.env import IrisResources


class IrisCommandContext(rv.manager.context.RevolioCommandContext):
    SERVICE = ('iris', 'irs')

    STACK = IrisResources
    ECR_STACK = revolio.architecture.resources.ecr.EcrResources

    SERVICE_CONTEXT = IrisContext

    class Component(enum.Enum):
        APP = ('web', 'app')
        NGX = ('web', 'ngx')


class IrisDevCommandContext(IrisCommandContext):
    env = revolio.manager.context.Env.DEV


class IrisProdCommandContext(IrisCommandContext):
    env = revolio.manager.context.Env.PROD
