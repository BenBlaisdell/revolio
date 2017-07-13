from revolio.architecture.resources.env import Env
from revolio.architecture.stack import resource_group

from nudge.infrastructure.resources.web import WebResources
from nudge.infrastructure.resources.worker import WorkerResources


class NudgeResources(Env):

    @resource_group
    def web(self):
        return WebResources(
            ctx=self._ctx,
            env=self,
        )

    @resource_group
    def worker(self):
        return WorkerResources(
            ctx=self._ctx,
            env=self,
        )
