from cached_property import cached_property

import troposphere as ts
import troposphere.cloudwatch
import troposphere.ecs
import troposphere.logs
import troposphere.sqs

import revolio as rv
from revolio.architecture.stack import resource, ResourceGroup, parameter
import revolio.manager.util

import nudge.infrastructure
from nudge.worker.deferral import DeferralWorker


class DeferralWorkerResources(ResourceGroup):

    @cached_property
    def queue_name(self):
        return self.config['S3Events']['QueueName']

    @cached_property
    def log_group_name(self):
        return self.config['LogGroupName']

    def __init__(self, ctx, env, cluster):
        super().__init__(ctx, env.config['Worker']['Deferral'], prefix='DeferralWorker')
        self.env = env
        self.ecs_cluster = cluster

    @resource
    def log_group(self):
        return ts.logs.LogGroup(
            self._get_logical_id('LogGroup'),
            LogGroupName=self.log_group_name,
            RetentionInDays=14,
        )

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
        return rv.manager.util.get_latest_image_tag(
            self.env.config['Ecr']['Repo']['Url'],
            *nudge.infrastructure.NudgeCommandContext.Component.DEF.value,
        )

    @resource
    def ecs_task_def(self):
        return ts.ecs.TaskDefinition(
            self._get_logical_id('TaskDefinition'),
            ContainerDefinitions=[ts.ecs.ContainerDefinition(
                    Name='def',
                    Image=ts.Ref(self.image),
                    Cpu=64,
                    Memory=256,
                    LogConfiguration=rv.manager.util.aws_logs_config(self.log_group_name),
                    Environment=rv.manager.util.env(
                        prefix=DeferralWorker.ENV_VAR_PREFIX,
                        variables={
                             DeferralWorker.QUEUE_URL_VAR: self.config['Env']['QueueUrl'],
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
            # no limits on the order of stopping / starting tasks
            # data remains in the queue and workers are gracefully shut down
            DeploymentConfiguration=ts.ecs.DeploymentConfiguration(
                MaximumPercent=200,
                MinimumHealthyPercent=0,
            ),
        )

    @resource
    def alarm(self):
        env = self.env.config['Tags']['Environment'].capitalize()
        return ts.cloudwatch.Alarm(
            self._get_logical_id('Alarm'),
            AlarmDescription=f'Nudge {env} Deferral DLQ alarm',
            Namespace='AWS/SQS',
            MetricName='NumberOfMessagesSent',
            Statistic='Sum',
            # https://stackoverflow.com/a/42635872
            # period needs to be 15 minutes for sqs
            Period=900,
            EvaluationPeriods=1,
            ComparisonOperator='GreaterThanThreshold',
            Threshold='0',
            AlarmActions=[ts.Ref(self.env.alerts_topic)],
            Dimensions=[ts.cloudwatch.MetricDimension(
                Name='QueueName',
                Value=ts.GetAtt(self.dlq, 'QueueName'),
            )],
        )
