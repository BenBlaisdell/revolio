import itertools

import awacs.aws
import awacs.autoscaling
import awacs.ecs
import awacs.helpers.trust
import awacs.logs
import awacs.sqs
from cached_property import cached_property

from nudge.worker.s3 import S3EventsWorker
from revolio import resource, parameter, ResourceGroup, SqsWorker
import troposphere as ts
import troposphere.autoscaling
import troposphere.cloudformation
import troposphere.ec2
import troposphere.ecs
import troposphere.iam
import troposphere.logs
import troposphere.sqs

import nudge.manager.util


class S3EventsWorkerResources(ResourceGroup):

    @cached_property
    def queue_name(self):
        return self.config['S3Events']['QueueName']

    def __init__(self, ctx, env, cluster, log_group_name):
        super().__init__(ctx, env.config['Worker']['S3Events'], prefix='S3EventsWorker')
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
    def queue_policy(self):
        return ts.sqs.QueuePolicy(
            self._get_logical_id('QueuePolicy'),
            Queues=[ts.Ref(self.queue)],
            PolicyDocument={
                'Version': '2012-10-17',
                'Statement': [{
                    'Sid': 'allow-s3-notifications',
                    'Effect': 'Allow',
                    'Principal': {
                      'AWS': '*'
                    },
                    'Action': ['sqs:SendMessage'],
                    'Resource': '*',
                    'Condition': {
                        # allow notifications from all buckets
                        'ArnLike': {'aws:SourceArn': 'arn:aws:s3:*:*:*'}
                    }
                }]
            },
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
        return nudge.manager.util.get_latest_image_tag(self.config['Repo'])

    @resource
    def ecs_task_def(self):
        return ts.ecs.TaskDefinition(
            self._get_logical_id('TaskDefinition'),
            ContainerDefinitions=[ts.ecs.ContainerDefinition(
                Name='s3e',
                Image=ts.Ref(self.image),
                Cpu=64,
                Memory=256,
                LogConfiguration=nudge.manager.util.aws_logs_config(self.log_group_name),
                Environment=nudge.manager.util.env(
                    prefix=S3EventsWorker.ENV_VAR_PREFIX,
                    variables={
                        SqsWorker.QUEUE_URL_VAR: self.config['Env']['QueueUrl'],
                        S3EventsWorker.HOST_VAR: self.config['Env']['NudgeHost'],
                        S3EventsWorker.PORT_VAR: self.config['Env']['NudgePort'],
                        S3EventsWorker.VERSION_VAR: self.config['Env']['NudgeVersion'],
                    },
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
        )
