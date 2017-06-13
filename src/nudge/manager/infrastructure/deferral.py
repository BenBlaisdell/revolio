from cached_property import cached_property

from revolio import resource, parameter, ResourceGroup, SqsWorker
import troposphere as ts
import troposphere.ecs
import troposphere.sqs

import nudge.manager.util
from nudge.worker.deferral import DeferralWorker


class DeferralWorkerResources(ResourceGroup):

    @cached_property
    def queue_name(self):
        return self.config['S3Events']['QueueName']

    def __init__(self, ctx, env, cluster, log_group_name):
        super().__init__(ctx, env.config['Worker']['Deferral'], prefix='DeferralWorker')
        self.env = env
        self.ecs_cluster = cluster
        self.log_group_name = log_group_name

    @resource
    def queue(self):
        return ts.sqs.Queue(
            self._get_logical_id('Queue'),
            QueueName=self.config['QueueName'],
            VisibilityTimeout=60*5,  # 5 minutes
            RedrivePolicy=ts.sqs.RedrivePolicy(
                deadLetterTargetArn=ts.GetAtt(self.dlq, 'Arn'),
                maxReceiveCount=3,
            ),
        )

    @resource
    def dlq(self):
        return ts.sqs.Queue(
            self._get_logical_id('Dlq'),
            QueueName=self.config['DlqName'],
        )

    @parameter
    def image(self):
        return ts.Parameter(
            self._get_logical_id('Image'),
            Type='String',
        )

    @image.value
    def image_value(self):
        return nudge.manager.util.get_latest_image_tag(self.env.config['Ecr']['Repos']['Env']['Url'], *nudge.manager.Component.DEF.value)

    @resource
    def ecs_task_def(self):
        return ts.ecs.TaskDefinition(
            self._get_logical_id('TaskDefinition'),
            ContainerDefinitions=[ts.ecs.ContainerDefinition(
                    Name='def',
                    Image=ts.Ref(self.image),
                    Cpu=64,
                    Memory=256,
                    LogConfiguration=nudge.manager.util.aws_logs_config(self.log_group_name),
                    Environment=nudge.manager.util.env(
                        prefix=DeferralWorker.ENV_VAR_PREFIX,
                        variables={
                             SqsWorker.QUEUE_URL_VAR: self.config['Env']['QueueUrl'],
                        }
                    ),
            )],
        )

    @resource
    def ecs_service(self):
        return ts.ecs.Service(
            self._get_logical_id('EcsService'),
            Cluster=ts.Ref(self.ecs_cluster),
            DesiredCount=2,
            TaskDefinition=ts.Ref(self.ecs_task_def),
            # no limits on the order of stopping / starting tasks
            # data remains in the queue and workers are gracefully shut down
            DeploymentConfiguration=ts.ecs.DeploymentConfiguration(
                MaximumPercent=200,
                MinimumHealthyPercent=0,
            ),
        )
