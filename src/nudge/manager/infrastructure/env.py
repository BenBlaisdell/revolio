import itertools
import logging

import awacs.autoscaling
import awacs.aws
import awacs.ec2
import awacs.ecs
import awacs.elasticloadbalancing
import awacs.events
import awacs.helpers.trust
import awacs.kms
import awacs.logs
import awacs.s3
import troposphere as ts
import troposphere.autoscaling
import troposphere.cloudformation
import troposphere.cloudwatch
import troposphere.ec2
import troposphere.ecs
import troposphere.elasticloadbalancing
import troposphere.iam
import troposphere.logs
import troposphere.sqs
import troposphere.route53
from cached_property import cached_property

import nudge.manager.util
from nudge.manager.infrastructure.db import DatabaseResources
from nudge.manager.infrastructure.secrets import SecretsResources
from nudge.manager.infrastructure.web import WebResources
from nudge.manager.infrastructure.worker import WorkerResources
from revolio.manager.stack import resource, resource_group, ResourceGroup


_logger = logging.getLogger(__name__)


class EnvResources(ResourceGroup):

    @cached_property
    def zones(self):
        return self.config['AvailabilityZones']

    @cached_property
    def ami(self):
        return self.config['Ec2ImageId']

    @cached_property
    def subnets(self):
        return self.config['Subnets']

    @cached_property
    def availability_zones(self):
        return self.config['AvailabilityZones']

    @cached_property
    def authorized_ips(self):
        return self.config['AuthorizedCidrIps']

    @cached_property
    def vpc_id(self):
        return self.config['VpcId']

    @cached_property
    def key_name(self):
        return self.config['KeyName']

    def __init__(self, ctx, config):
        super().__init__(ctx, config)

    @cached_property
    def events_queue_name(self):
        return self._config['EventsQueueName']

    @resource
    def events_queue(self):
        return ts.sqs.Queue(
            self._get_logical_id('EventsQueue'),
            QueueName=self.events_queue_name,
            VisibilityTimeout=60*5,  # 5 minutes
        )

    @resource_group
    def secrets(self):
        return SecretsResources(self._ctx, self)

    @resource_group
    def web(self):
        return WebResources(self._ctx, self)

    @resource_group
    def worker(self):
        return WorkerResources(self._ctx, self)

    @resource_group
    def db_resources(self):
        return DatabaseResources(self._ctx, self)
