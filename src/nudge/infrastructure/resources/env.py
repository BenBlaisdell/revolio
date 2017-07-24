import troposphere as ts
import troposphere.sns

from revolio.architecture.resources.env import Env
from revolio.architecture.stack import resource_group, resource

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

    @resource
    def alerts_topic(self):
        return ts.sns.Topic(
            self._get_logical_id('AlertsTopic'),
            TopicName=self.config['Alerts']['TopicName'],
            Subscription=[
                ts.sns.Subscription(Protocol='email', Endpoint=address)
                for address in self.config['Alerts']['Emails']
            ],
        )
