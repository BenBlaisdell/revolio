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
import awacs.sqs
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
from revolio.manager.stack import resource, parameter, ResourceGroup


_logger = logging.getLogger(__name__)


class WebResources(ResourceGroup):

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
    def key_name(self):
        return self.env.key_name

    @cached_property
    def ami(self):
        return self.env.ami

    @cached_property
    def zones(self):
        return self.env.zones

    @cached_property
    def secrets_bucket(self):
        return self.env.secrets.bucket

    @cached_property
    def cluster_name(self):
        return self.config['ClusterName']

    @cached_property
    def hosted_zone_name(self):
        return self.config['HostedZoneName']

    @cached_property
    def record_set_name(self):
        return self.config['RecordSetName']

    @cached_property
    def ec2_instance_type(self):
        return self.config['InstanceType']

    @cached_property
    def secrets_key_arn(self):
        return ts.GetAtt(self.env.secrets.key, 'Arn')

    @cached_property
    def s3_config_uri(self):
        return 's3://{}/{}'.format(self.env.secrets.bucket_name, self.env.secrets.config_key)

    @cached_property
    def app_repo_uri(self):
        return self.config['Repos']['App']

    @cached_property
    def nginx_repo_uri(self):
        return self.config['Repos']['Nginx']

    @cached_property
    def log_group_name(self):
        return self._config['LogGroupName']

    def __init__(self, ctx, env):
        super().__init__(ctx, env.config['Web'], prefix='Web')
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
    def app_image(self):
        return ts.Parameter(
            self._get_logical_id('AppImage'),
            Type='String',
        )

    @app_image.value
    def app_image_value(self):
        return nudge.manager.util.get_latest_image_tag(self.app_repo_uri)

    @cached_property
    def app_container_def(self):
        return ts.ecs.ContainerDefinition(
            Name='app',
            Image=ts.Ref(self.app_image),
            Cpu=64,
            Memory=256,
            PortMappings=[ts.ecs.PortMapping(
                # todo: move to config file
                HostPort=9091,
                ContainerPort=9091,
            )],
            LogConfiguration=nudge.manager.util.aws_logs_config(self.log_group_name, 'app'),
            Environment=nudge.manager.util.env(
                # todo: get from load location
                S3_CONFIG_URI=self.s3_config_uri,
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
        return nudge.manager.util.get_latest_image_tag(self.nginx_repo_uri)

    @cached_property
    def nginx_container_def(self):
        return ts.ecs.ContainerDefinition(
            Name='nginx',
            Image=ts.Ref(self.nginx_image),
            Cpu=64,
            Memory=256,
            PortMappings=[ts.ecs.PortMapping(
                # todo: move to config file
                HostPort=8080,
                ContainerPort=8080,
            )],
            LogConfiguration=nudge.manager.util.aws_logs_config(self.log_group_name, 'nginx'),
            VolumesFrom=[ts.ecs.VolumesFrom(SourceContainer=self.app_container_def.Name)],
        )

    @resource
    def ecs_task_def(self):
        return ts.ecs.TaskDefinition(
            self._get_logical_id('TaskDefinition'),
            ContainerDefinitions=[
                self.nginx_container_def,
                self.app_container_def,
            ],
        )

    @resource
    def ecs_service_role(self):
        return ts.iam.Role(
            self._get_logical_id('ServiceRole'),
            AssumeRolePolicyDocument=awacs.aws.Policy(
                Statement=[awacs.helpers.trust.make_simple_assume_statement('ecs.amazonaws.com')],
            ),
            Path='/',
            Policies=[ts.iam.Policy(
                PolicyName='dwh-nudge-web',
                PolicyDocument=awacs.aws.Policy(
                    Statement=[awacs.aws.Statement(
                        Effect='Allow',
                        Action=[
                            awacs.elasticloadbalancing.Action('Describe*'),
                            awacs.elasticloadbalancing.DeregisterInstancesFromLoadBalancer,
                            awacs.elasticloadbalancing.RegisterInstancesWithLoadBalancer,
                            awacs.ec2.Action('Describe*'),
                            awacs.ec2.AuthorizeSecurityGroupIngress,
                        ],
                        Resource=['*'],
                    )],
                ),
            )],
        )

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
                        'access-deferral-queue',
                        awacs.aws.Statement(
                            Effect='Allow',
                            Action=[awacs.sqs.Action('*')],
                            Resource=[ts.GetAtt(self.env.worker.def_worker.queue, 'Arn')],
                        ),
                    ), (
                        'read-all-s3',
                        awacs.aws.Statement(
                            Effect='Allow',
                            Action=[
                                awacs.s3.Action('List*'),
                                awacs.s3.Action('Get*'),
                            ],
                            Resource=['*'],
                        ),
                    ), (
                        # allow pulling s3 config
                        'access-secrets-bucket',
                        awacs.aws.Statement(
                            Effect='Allow',
                            Action=[awacs.s3.Action('*')],
                            Resource=[ts.Join('', ['arn:aws:s3:::', ts.Ref(self.secrets_bucket), '*'])],
                        ),
                    ), (
                        # allow decrypting s3 secrets
                        'use-secrets-kms-key',
                        awacs.aws.Statement(
                            Effect='Allow',
                            Action=[awacs.kms.Action('*')],
                            Resource=[self.secrets_key_arn],
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

    @resource
    def ecs_service(self):
        return ts.ecs.Service(
            self._get_logical_id('EcsService'),
            Cluster=ts.Ref(self.ecs_cluster),
            DesiredCount=2,
            LoadBalancers=[ts.ecs.LoadBalancer(
                ContainerName='nginx',
                ContainerPort=8080,
                LoadBalancerName=ts.Ref(self.elastic_load_balancer),
            )],
            Role=ts.Ref(self.ecs_service_role),
            TaskDefinition=ts.Ref(self.ecs_task_def),
            # allow ecs to stop and replace tasks
            # port usage prevents replacement otherwise
            DeploymentConfiguration=ts.ecs.DeploymentConfiguration(
                MaximumPercent=100,
                MinimumHealthyPercent=50,
            ),
        )

    @resource
    def security_group(self):
        return ts.ec2.SecurityGroup(
            self._get_logical_id('SecurityGroup'),
            GroupDescription='Nudge Web Security Group',
            VpcId=self.vpc_id,
            SecurityGroupIngress=[
                ts.ec2.SecurityGroupRule(
                    IpProtocol='tcp',
                    FromPort=lower,
                    ToPort=upper,
                    CidrIp=ip,
                )
                for lower, upper in [
                    (80, 8080),  # api
                    (22, 22),    # ssh
                ]
                for ip in itertools.chain(
                    ['10.0.0.0/8', '172.16.0.0/12'],  # addresses inside vpc
                    self.authorized_ips,
                )
            ],
        )

    @resource
    def elastic_load_balancer(self):
        return ts.elasticloadbalancing.LoadBalancer(
            self._get_logical_id('Elb'),
            CrossZone=True,
            Scheme='internet-facing',
            Subnets=self.subnets,
            SecurityGroups=[ts.Ref(self.security_group)],
            Listeners=[ts.elasticloadbalancing.Listener(
                LoadBalancerPort=80,
                InstancePort=8080,
                Protocol='HTTP',
            )],
            HealthCheck=ts.elasticloadbalancing.HealthCheck(
                # todo: get from definition of call endpoint
                Target='HTTP:8080/api/1/call/CheckHealth/',
                HealthyThreshold=2,
                UnhealthyThreshold=7,
                Interval=30,
                Timeout=10,
            ),
            ConnectionDrainingPolicy=ts.elasticloadbalancing.ConnectionDrainingPolicy(
                Enabled=True,
                Timeout=300,
            ),
        )

    @resource
    def record_set_group(self):
        return ts.route53.RecordSetGroup(
            self._get_logical_id('RecordSetGroup'),
            HostedZoneName=self.hosted_zone_name,
            RecordSets=[ts.route53.RecordSet(
                Name=self.record_set_name,
                Type='A',
                AliasTarget=ts.route53.AliasTarget(
                    EvaluateTargetHealth=False,
                    DNSName=ts.GetAtt(self.elastic_load_balancer, 'CanonicalHostedZoneName'),
                    HostedZoneId=ts.GetAtt(self.elastic_load_balancer, 'CanonicalHostedZoneNameID'),
                ),
            )],
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
            MinSize=2,
            MaxSize=5,
            HealthCheckType='ELB',
            HealthCheckGracePeriod=900,
            LoadBalancerNames=[ts.Ref(self.elastic_load_balancer)],
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


class Scaling(ResourceGroup):

    def __init__(self, prefix, autoscaling_group):
        super(Scaling, self).__init__({}, prefix=prefix)
        self.autoscaling_group = autoscaling_group

    @resource
    def scale_up_policy(self):
        return ts.autoscaling.ScalingPolicy(
            self._get_logical_id('ScaleUpPolicy'),
            AdjustmentType='ChangeInCapacity',
            AutoscalingGroupName=ts.Ref(self.autoscaling_group),
            Cooldown=60,
            ScalingAdjustment=1,
        )

    @resource
    def cpu_alarm_high(self):
        return ts.cloudwatch.Alarm(
            self._get_logical_id('CPUAlarmHigh'),
            AlarmDescription='Scale up if CPU > 90% for 10 minutes',
            MetricName='CPUUtilization',
            Namespace='AWS/EC2',
            Statistic='Average',
            Period=300,
            EvaluationThreshold=2,
            Threshold=90,
            AlarmActions=[ts.Ref(self.scale_up_policy)],
            Dimensions=[ts.cloudwatch.MetricDimension(
                Name='AutoScalingGroupName',
                Value=ts.Ref(self.autoscaling_group),
            )],
            ComparisonOperator='GreaterThanThreshold',
        )

    @resource
    def scale_down_policy(self):
        return ts.autoscaling.ScalingPolicy(
            self._get_logical_id('ScaleDownPolicy'),
            AdjustmentType='ChangeInCapacity',
            AutoscalingGroupName=ts.Ref(self.autoscaling_group),
            Cooldown=60,
            ScalingAdjustment=-1,
        )

    @resource
    def cpu_alarm_low(self):
        return ts.cloudwatch.Alarm(
            self._get_logical_id('CPUAlarmLow'),
            AlarmDescription='Scale down if CPU < 90% for 10 minutes',
            MetricName='CPUUtilization',
            Namespace='AWS/EC2',
            Statistic='Average',
            Period=300,
            EvaluationThreshold=2,
            Threshold=70,
            AlarmActions=[ts.Ref(self.scale_down_policy)],
            Dimensions=[ts.cloudwatch.MetricDimension(
                Name='AutoScalingGroupName',
                Value=ts.Ref(self.autoscaling_group),
            )],
            ComparisonOperator='LessThanThreshold',
        )



