import collections

import awacs.aws
import awacs.s3
import awacs.sns
from cached_property import cached_property
import troposphere as ts
import troposphere.ecs

import revolio.architecture.resources.web
import revolio.manager
import revolio.manager.util
from revolio.architecture.stack import resource, parameter

import iris.core.context
import iris.infrastructure


class WebResources(revolio.architecture.resources.web.WebResources):

    @property
    def profile_role_statements(self):
        return collections.ChainMap(
            {
                's3-notifications': awacs.aws.Statement(
                    Effect='Allow',
                    Action=[
                        awacs.s3.GetBucketNotification,
                        awacs.s3.PutBucketNotification,
                    ],
                    # todo: restrict to single test bucket if not prod
                    Resource=['*'],
                ),
                'sns': awacs.aws.Statement(
                    Effect='Allow',
                    Action=[awacs.sns.Action('*')],
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
        return revolio.manager.util.get_latest_image_tag(self.env.config['Ecr']['Repo']['Url'], *iris.infrastructure.IrisCommandContext.Component.APP.value)

    @cached_property
    def app_container_def(self):
        return ts.ecs.ContainerDefinition(
            Name='app',
            Image=ts.Ref(self.app_image),
            Cpu=64,
            Memory=256,
            LogConfiguration=revolio.manager.util.aws_logs_config(self.log_group_name),
            Environment=revolio.manager.util.env(
                prefix=iris.core.context.IrisConfigService.ENV_VAR_PREFIX,
                variables={
                     iris.core.context.IrisConfigService.S3_CONFIG_URI: self.s3_config_uri,
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
        return revolio.manager.util.get_latest_image_tag(self.env.config['Ecr']['Repo']['Url'], *iris.infrastructure.IrisCommandContext.Component.NGX.value)

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
