import enum

import revolio as rv
import revolio.architecture.resources.ecr
import revolio.manager.context

from nudge.core.context import NudgeCoreContext
from nudge.infrastructure.resources.env import NudgeResources


class NudgeCommandContext(rv.manager.context.RevolioCommandContext):
    SERVICE = ('nudge', 'ndg')

    STACK = NudgeResources
    ECR_STACK = revolio.architecture.resources.ecr.EcrResources

    SERVICE_CONTEXT = NudgeCoreContext

    class Component(enum.Enum):
        APP = ('web', 'app')
        NGX = ('web', 'ngx')
        S3E = ('wrk', 's3e')
        DEF = ('wrk', 'def')


class NudgeDevCommandContext(NudgeCommandContext):
    env = rv.manager.context.Env.DEV


class NudgeStageCommandContext(NudgeCommandContext):
    env = rv.manager.context.Env.STAGE


class NudgeProdCommandContext(NudgeCommandContext):
    env = rv.manager.context.Env.PROD
