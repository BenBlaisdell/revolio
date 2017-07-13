from revolio.architecture.resources.env import Env
from revolio.architecture.stack import resource_group

from iris.infrastructure.resources.web import WebResources


class IrisResources(Env):

    def __init__(self, ctx, config):
        super().__init__(ctx, config)

    @resource_group
    def web(self):
        return WebResources(
            ctx=self._ctx,
            env=self,
        )
