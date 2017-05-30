import itertools

import awacs.aws
import awacs.autoscaling
import awacs.ecs
import awacs.helpers.trust
import awacs.logs
import awacs.sqs
from cached_property import cached_property
from revolio import resource, parameter, ResourceGroup
import troposphere as ts
import troposphere.autoscaling
import troposphere.cloudformation
import troposphere.ec2
import troposphere.ecs
import troposphere.iam
import troposphere.logs

import nudge.manager.util


class WorkerResources(ResourceGroup):

    @cached_property
    def queue_arn(self):
        return ts.GetAtt(self.env.events_queue, 'Arn')

    @cached_property
    def queue_url(self):
        return self.config['QueueUrl']

    @cached_property
    def authorized_ips(self):
        return self.env.authorized_ips

    @cached_property
    def ec2_instance_type(self):
        return self.config['InstanceType']

    @cached_property
    def vpc_id(self):
        return self.env.vpc_id

    @cached_property
    def key_name(self):
        return self.env.key_name

    @cached_property
    def ami(self):
        return self.env.ami

    @cached_property
    def subnets(self):
        return self.env.subnets

    @cached_property
    def zones(self):
        return self.env.zones

    @cached_property
    def nudge_host(self):
        return self.config['NudgeHost']

    @cached_property
    def nudge_port(self):
        return self.config['NudgePort']

    @cached_property
    def nudge_version(self):
        return self.config['NudgeVersion']

    @cached_property
    def cluster_name(self):
        return 'nudge-worker'

    @cached_property
    def worker_repo_uri(self):
        return self.env.config['Repos']['Worker']

    @cached_property
    def log_group_name(self):
        return self.config['LogGroupName']

    def __init__(self, ctx, env):
        super().__init__(ctx, env.config['Worker'], prefix='Worker')
        self.env = env

    @resource
    def log_group(self):
        return ts.logs.LogGroup(
            self._get_logical_id('LogGroup'),
            LogGroupName=self.log_group_name,
            RetentionInDays=14,
        )

    @resource
    def ecs_cluster(self):
        return ts.ecs.Cluster(
            self._get_logical_id('EcsCluster'),
            ClusterName=self.cluster_name,
        )

    @parameter
    def worker_image(self):
        return ts.Parameter(
            self._get_logical_id('WorkerImage'),
            Type='String',
        )

    @worker_image.value
    def worker_version_value(self):
        return nudge.manager.util.get_latest_image_tag(self.worker_repo_uri)

    @resource
    def ecs_task_def(self):
        return ts.ecs.TaskDefinition(
            self._get_logical_id('TaskDefinition'),
            ContainerDefinitions=[ts.ecs.ContainerDefinition(
                Name='worker',
                Image=ts.Ref(self.worker_image),
                Cpu=64,
                Memory=256,
                LogConfiguration=nudge.manager.util.aws_logs_config(self.log_group_name, 'worker'),
                Environment=nudge.manager.util.env(
                    # todo: get from load location
                    NUDGE_HOST=self.nudge_host,
                    NUDGE_PORT=self.nudge_port,
                    NUDGE_VERSION=self.nudge_version,
                    NUDGE_NOTIFICATION_QUEUE_URL=self.queue_url,
                ),
            )],
        )

    @resource
    def security_group(self):
        return ts.ec2.SecurityGroup(
            self._get_logical_id('SecurityGroup'),
            GroupDescription='Nudge Worker Security Group',
            VpcId=self.vpc_id,
            SecurityGroupIngress=[
                ts.ec2.SecurityGroupRule(
                    IpProtocol='tcp',
                    FromPort=22,
                    ToPort=22,
                    CidrIp=ip,
                )
                for ip in itertools.chain(
                    ['10.0.0.0/8', '172.16.0.0/12'],  # addresses inside vpc
                    self.authorized_ips,
                )
            ],
        )

    @resource
    def ecs_service(self):
        return ts.ecs.Service(
            self._get_logical_id('EcsService'),
            Cluster=ts.Ref(self.ecs_cluster),
            DesiredCount=2,
            TaskDefinition=ts.Ref(self.ecs_task_def),
        )

    # ec2 instance autoscaling

    @cached_property
    def launch_config_logical_id(self):
        return self._get_logical_id('LaunchConfiguration')

    @cached_property
    def auto_scaling_group_logical_id(self):
        return self._get_logical_id('AutoScalingGroup')

    @resource
    def ec2_auto_scaling_group(self):
        return ts.autoscaling.AutoScalingGroup(
            self.auto_scaling_group_logical_id,
            LaunchConfigurationName=ts.Ref(self.ec2_launch_config),
            VPCZoneIdentifier=self.subnets,
            AvailabilityZones=self.zones,
            MinSize=1,
            MaxSize=5,
            HealthCheckType='ELB',
            HealthCheckGracePeriod=900,
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
                                'path=Resources.{}.Metadata.AWS::CloudFormation::Init'.format(self.launch_config_logical_id), '\n',
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
            '#!/bin/bash -xe', '\n',
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
            Policies=[
                ts.iam.Policy(
                    PolicyName='nudge-{}'.format(name),
                    PolicyDocument=awacs.aws.Policy(
                        Version='2012-10-17',
                        Statement=[statement],
                    ),
                ) for name, statement in [
                    (
                        # poll s3 events queue
                        'sqs',
                        awacs.aws.Statement(
                            Effect='Allow',
                            Action=[awacs.sqs.Action('*')],
                            Resource=[self.queue_arn],
                        ),
                    ), (
                        # register instance in cluster
                        'ecs',
                        awacs.aws.Statement(
                            Effect='Allow',
                            Action=[awacs.ecs.Action('*')],
                            Resource=['*'],
                        ),
                    ), (
                        # publish container logs to log group
                        'logs',
                        awacs.aws.Statement(
                            Effect='Allow',
                            Action=[awacs.logs.Action('*')],
                            Resource=['*'],
                        ),
                    ), (
                        'autoscaling',
                        awacs.aws.Statement(
                            Effect='Allow',
                            Action=[awacs.autoscaling.Action('*')],
                            Resource=['*'],
                        ),
                    ),
                ]
            ],
        )

    @resource
    def ec2_instance_profile(self):
        return ts.iam.InstanceProfile(
            self._get_logical_id('InstanceProfile'),
            Path='/',
            Roles=[ts.Ref(self.ec2_instance_profile_role)],
        )
