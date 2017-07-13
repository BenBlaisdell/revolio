import collections
import itertools

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
import troposphere.autoscaling
import troposphere.cloudformation
import troposphere.ec2
import troposphere.ecs
import troposphere.iam

from revolio.architecture.stack import resource, resource_group, ResourceGroup


class EcsResources(ResourceGroup):

    @cached_property
    def cluster_name(self):
        return self.config['ClusterName']

    @resource
    def ecs_cluster(self):
        return ts.ecs.Cluster(
            self._get_logical_id('EcsCluster'),
            ClusterName=self.cluster_name,
        )

    @cached_property
    def key_name(self):
        return self.env.key_name

    @cached_property
    def ami(self):
        return self.env.ami

    @cached_property
    def zones(self):
        return self.env.zones

    @cached_property
    def subnets(self):
        return self.env.subnets

    @cached_property
    def authorized_ips(self):
        return self.env.authorized_ips

    @cached_property
    def vpc_id(self):
        return self.env.vpc_id

    @cached_property
    def hosted_zone_name(self):
        return self.config['HostedZoneName']

    @cached_property
    def ec2_instance_type(self):
        return self.config['InstanceType']

    def __init__(self, ctx, config, env, prefix):
        super().__init__(ctx, config, prefix=prefix)
        self.env = env

    @resource
    def ec2_instance_profile_role(self):
        return ts.iam.Role(
            self._get_logical_id('InstanceProfileRole'),
            AssumeRolePolicyDocument=awacs.aws.Policy(
                Statement=[awacs.helpers.trust.make_simple_assume_statement('ec2.amazonaws.com')],
            ),
            Path='/',
            ManagedPolicyArns=[
                'arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceRole',
                'arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly',
            ],
            Policies=[ts.iam.Policy(
                PolicyName=f'{self.project_name}-{statement_name}',
                PolicyDocument=awacs.aws.Policy(
                    Version='2012-10-17',
                    Statement=[statement],
                ),
            ) for statement_name, statement in collections.ChainMap(self.profile_role_statements, {
                # register instance in cluster
                'ecs': awacs.aws.Statement(
                    Effect='Allow',
                    Action=[awacs.ecs.Action('*')],
                    Resource=['*'],
                ),
                # publish container logs to log group
                'logs': awacs.aws.Statement(
                    Effect='Allow',
                    Action=[awacs.logs.Action('*')],
                    Resource=['*'],
                ),
                'autoscaling': awacs.aws.Statement(
                    Effect='Allow',
                    Action=[awacs.autoscaling.Action('*')],
                    Resource=['*'],
                ),
            }).items()],
        )

    @property
    def profile_role_statements(self):
        return {
            # 'statement-description': awacs.aws.Statement(
            #     Effect='Allow',
            #     Action=[awacs.service.Action('*')],
            #     Resource=['*'],
            # ),
        }

    @resource
    def ec2_instance_profile(self):
        return ts.iam.InstanceProfile(
            self._get_logical_id('InstanceProfile'),
            Path='/',
            Roles=[ts.Ref(self.ec2_instance_profile_role)],
        )

    @resource
    def security_group(self):
        return ts.ec2.SecurityGroup(
            self._get_logical_id('SecurityGroup'),
            GroupDescription=f'{self.project_name.capitalize()} {self._prefix} Security Group',
            VpcId=self.vpc_id,
            SecurityGroupIngress=[
                ts.ec2.SecurityGroupRule(
                    IpProtocol='tcp',
                    FromPort=lower,
                    ToPort=upper,
                    CidrIp=ip,
                )
                for lower, upper in [
                    (32768, 61000),  # ephemeral nginx ports
                    (8080, 8080),
                    (22, 22),        # ssh
                ]
                for ip in itertools.chain(
                    ['10.0.0.0/8', '172.16.0.0/12'],  # addresses inside vpc
                    self.authorized_ips,
                )
            ],
        )

    @cached_property
    def launch_config_logical_id(self):
        return self._get_logical_id('LaunchConfiguration')

    @cached_property
    def auto_scaling_group_logical_id(self):
        return self._get_logical_id('AutoScalingGroup')

    @resource
    def ec2_autoscaling_group(self):
        return ts.autoscaling.AutoScalingGroup(
            self.auto_scaling_group_logical_id,
            LaunchConfigurationName=ts.Ref(self.ec2_launch_config),
            VPCZoneIdentifier=self.subnets,
            AvailabilityZones=self.zones,
            MinSize=1,
            MaxSize=5,
            HealthCheckType='EC2',
            HealthCheckGracePeriod=900,
            # TargetGroupARNs=[
            #     ts.Ref(self.external.target_group),
            #     ts.Ref(self.internal.target_group),
            # ],
            # don't launch service until config is uploaded
            # DependsOn=self.env.secrets.wait_condition.title,
        )

    @resource
    def ec2_launch_config(self):
        return ts.autoscaling.LaunchConfiguration(
            self.launch_config_logical_id,
            KeyName=self.key_name,
            ImageId=self.ami,
            AssociatePublicIpAddress=True,
            SecurityGroups=[ts.Ref(self.security_group)],
            IamInstanceProfile=ts.Ref(self.ec2_instance_profile),
            InstanceType=self.ec2_instance_type,
            Metadata=self.ec2_metadata,
            UserData=self.ec2_user_data,
        )

    @cached_property
    def ec2_metadata(self):
        return ts.autoscaling.Metadata(
            ts.cloudformation.Init({
                'config': ts.cloudformation.InitConfig(
                    files=ts.cloudformation.InitFiles({
                        '/etc/cfn/cfn-hup.conf': ts.cloudformation.InitFile(
                            content=ts.Join('', [
                                '[main]', '\n',
                                'stack=', ts.Ref('AWS::StackId'), '\n',
                                'region=', ts.Ref('AWS::Region'), '\n',
                            ]),
                            mode='000400',
                            owner='root',
                            group='root',
                        ),
                        '/etc/cfn/hooks.d/cfn-auto-reloader.conf': ts.cloudformation.InitFile(
                            content=ts.Join('', [
                                '[cfn-auto-reloader-hook]', '\n',
                                'triggers=post.update', '\n',
                                f'path=Resources.{self.launch_config_logical_id}.Metadata.AWS::CloudFormation::Init', '\n',
                                'action=/opt/aws/bin/cfn-init -v ',
                                '    --stack    ', ts.Ref('AWS::StackName'),
                                '    --resource ', self.launch_config_logical_id,
                                '    --region   ', ts.Ref('AWS::Region'), '\n',
                                'runas=root', '\n',
                            ]),
                            mode='000400',
                            owner='root',
                            group='root',
                        )},
                    ),
                    services=ts.cloudformation.InitServices({
                        'cfn-hup': ts.cloudformation.InitService(
                            ensureRunning='true',
                            enabled='true',
                            files=['/etc/cfn/cfn-hup.conf', '/etc/cfn/hooks.d/cfn-auto-reloader.conf'],
                        )},
                    ),
                    commands={
                        # https://docs.aws.amazon.com/AmazonECS/latest/developerguide/launch_container_instance.html
                        '01_add_instance_to_cluster': {'command': ts.Join('', [
                            '#!/bin/bash', '\n',
                            'echo ECS_CLUSTER=', ts.Ref(self.ecs_cluster), ' >> /etc/ecs/ecs.config',
                        ])},
                        # https://docs.aws.amazon.com/systems-manager/latest/userguide/what-is-systems-manager.html
                        '02_install_ssm_agent': {'command': ts.Join('', [
                            '#!/bin/bash', '\n',
                            'yum -y update', '\n',
                            'curl https://amazon-ssm-eu-west-1.s3.amazonaws.com/latest/linux_amd64/amazon-ssm-agent.rpm -o amazon-ssm-agent.rpm', '\n',
                            'yum install -y amazon-ssm-agent.rpm',
                        ])},
                    },
                ),
            }),
        )

    @cached_property
    def ec2_user_data(self):
        return ts.Base64(ts.Join('', [
            # -x print commands as they're executed
            # -e exit on error
            '#!/bin/bash -xe', '\n',
            # todo: figure out what these commands do
            'yum install -y aws-cfn-bootstrap', '\n',
            '/opt/aws/bin/cfn-init -v ',
            '    --stack    ', ts.Ref('AWS::StackName'),
            '    --resource ', self.launch_config_logical_id,
            '    --region   ', ts.Ref('AWS::Region'),
            '\n',
            '/opt/aws/bin/cfn-signal -e $? ',
            '     --stack   ', ts.Ref('AWS::StackName'),
            '    --resource ', self.auto_scaling_group_logical_id,
            '    --region   ', ts.Ref('AWS::Region'),
            '\n',
        ]))
