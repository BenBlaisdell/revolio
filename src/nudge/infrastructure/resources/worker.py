import collections

import awacs.autoscaling
import awacs.aws
import awacs.ecs
import awacs.helpers.trust
import awacs.logs
import awacs.sqs
import troposphere as ts

from revolio.architecture.resources.ecs import EcsResources
from revolio.architecture.stack import resource_group

from nudge.infrastructure.resources.deferral import DeferralWorkerResources
from nudge.infrastructure.resources.s3_events import S3EventsWorkerResources


class WorkerResources(EcsResources):

    def __init__(self, ctx, env):
        super().__init__(ctx, env.config['Worker'], env, prefix='Worker')
        self.env = env

    @resource_group
    def s3e_worker(self):
        return S3EventsWorkerResources(
            self._ctx,
            self.env,
            self.ecs_cluster,
        )

    @resource_group
    def def_worker(self):
        return DeferralWorkerResources(
            self._ctx,
            self.env,
            self.ecs_cluster,
        )

    @property
    def profile_role_statements(self):
        return collections.ChainMap(
            {
                # poll s3 events queue
                'sqs': awacs.aws.Statement(
                    Effect='Allow',
                    Action=[awacs.sqs.Action('*')],
                    Resource=[
                        ts.GetAtt(self.s3e_worker.queue, 'Arn'),
                        ts.GetAtt(self.def_worker.queue, 'Arn'),
                    ],
                ),
            },
            super().profile_role_statements,
        )
