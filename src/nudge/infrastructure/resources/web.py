import collections

import awacs.application_autoscaling
import awacs.autoscaling
import awacs.aws
import awacs.cloudwatch
import awacs.ec2
import awacs.ecs
import awacs.elasticloadbalancing
import awacs.events
import awacs.helpers.trust
import awacs.kms
import awacs.logs
import awacs.s3
import awacs.sqs
from cached_property import cached_property
import troposphere as ts
import troposphere.ecs

import revolio as rv
import revolio.architecture.resources.web
from revolio.architecture.stack import resource, parameter
import revolio.manager.util

from nudge.core.context import NudgeConfigService
import nudge.infrastructure


class WebResources(revolio.architecture.resources.web.WebResources):

    @property
    def profile_role_statements(self):
        return collections.ChainMap(
            {
                # send trigger messages
                'access-all-sqs': awacs.aws.Statement(
                    Effect='Allow',
                    Action=[awacs.sqs.Action('*')],
                    Resource=['*'],
                ),
                # send deferred api calls
                'access-deferral-queue': awacs.aws.Statement(
                    Effect='Allow',
                    Action=[awacs.sqs.Action('*')],
                    Resource=[ts.GetAtt(self.env.worker.def_worker.queue, 'Arn')],
                ),
                # backfill data
                'read-all-s3': awacs.aws.Statement(
                    Effect='Allow',
                    Action=[
                        awacs.s3.Action('List*'),
                        awacs.s3.Action('Get*'),
                    ],
                    Resource=['*'],
                ),
            },
            super().profile_role_statements,
        )

    @parameter
    def app_image(self):
        return ts.Parameter(
            self._get_logical_id('AppImage'),
            Type='String',
        )

    @app_image.value
    def app_image_value(self):
        return rv.manager.util.get_latest_image_tag(self.env.config['Ecr']['Repo']['Url'], *nudge.infrastructure.NudgeCommandContext.Component.APP.value)

    @cached_property
    def app_container_def(self):
        return ts.ecs.ContainerDefinition(
            Name='app',
            Image=ts.Ref(self.app_image),
            Cpu=64,
            Memory=256,
            LogConfiguration=rv.manager.util.aws_logs_config(self.log_group_name),
            Environment=rv.manager.util.env(
                prefix=NudgeConfigService.ENV_VAR_PREFIX,
                variables={
                     NudgeConfigService.S3_CONFIG_URI: self.s3_config_uri,
                },
            ),
        )

    @parameter
    def nginx_image(self):
        return ts.Parameter(
            self._get_logical_id('NginxImage'),
            Type='String',
        )

    @nginx_image.value
    def nginx_version_value(self):
        return rv.manager.util.get_latest_image_tag(self.env.config['Ecr']['Repo']['Url'], *nudge.infrastructure.NudgeCommandContext.Component.NGX.value)

    @cached_property
    def nginx_container_def(self):
        return ts.ecs.ContainerDefinition(
            Name='nginx',
            Image=ts.Ref(self.nginx_image),
            Cpu=64,
            Memory=256,
            PortMappings=[ts.ecs.PortMapping(
                # todo: move to config file
                HostPort=0,  # dynamically generated
                ContainerPort=8080,
            )],
            LogConfiguration=revolio.manager.util.aws_logs_config(self.log_group_name),
            VolumesFrom=[ts.ecs.VolumesFrom(SourceContainer=self.app_container_def.Name)],
        )

    @resource
    def task_def(self):
        return ts.ecs.TaskDefinition(
            self._get_logical_id('TaskDefinition'),
            ContainerDefinitions=[
                self.nginx_container_def,
                self.app_container_def,
            ],
        )
