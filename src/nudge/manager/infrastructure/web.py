import itertools
import logging

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
import troposphere as ts
import troposphere.applicationautoscaling
import troposphere.autoscaling
import troposphere.cloudformation
import troposphere.cloudwatch
import troposphere.ec2
import troposphere.ecs
import troposphere.elasticloadbalancingv2
import troposphere.iam
import troposphere.logs
import troposphere.sqs
import troposphere.route53
from cached_property import cached_property

import nudge.manager
import nudge.manager.util
from nudge.core.config import ConfigService
from revolio.manager.stack import resource, resource_group, parameter, ResourceGroup


_logger = logging.getLogger(__name__)


class WebResources(ResourceGroup):

    @cached_property
    def external_service_name(self):
        return self.config['External']['ServiceName']

    @cached_property
    def external_elb_name(self):
        return self.config['External']['ElbName']

    @cached_property
    def external_target_group_name(self):
        return self.config['External']['TargetGroupName']

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
                        # send trigger messages
                        'access-all-sqs',
                        awacs.aws.Statement(
                            Effect='Allow',
                            Action=[awacs.sqs.Action('*')],
                            Resource=['*'],
                        ),
                    ), (
                        # send deferred api calls
                        'access-deferral-queue',
                        awacs.aws.Statement(
                            Effect='Allow',
                            Action=[awacs.sqs.Action('*')],
                            Resource=[ts.GetAtt(self.env.worker.def_worker.queue, 'Arn')],
                        ),
                    ), (
                        # backfill data
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
            TargetGroupARNs=[
                ts.Ref(self.external.target_group),
                ts.Ref(self.internal.target_group),
            ],
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

    # @resource
    # def scale_up_policy(self):
    #     return ts.autoscaling.ScalingPolicy(
    #         self._get_logical_id('ScaleUpPolicy'),
    #         AdjustmentType='ChangeInCapacity',
    #         AutoscalingGroupName=ts.Ref(self.ec2_autoscaling_group),
    #         Cooldown=60,
    #         ScalingAdjustment=1,
    #     )
    #
    # @resource
    # def cpu_alarm_high(self):
    #     return ts.cloudwatch.Alarm(
    #         self._get_logical_id('CPUAlarmHigh'),
    #         AlarmDescription='Scale up if CPU > 90% for 10 minutes',
    #         MetricName='CPUUtilization',
    #         Namespace='AWS/EC2',
    #         Statistic='Average',
    #         Period=300,
    #         EvaluationThreshold=2,
    #         Threshold=90,
    #         AlarmActions=[ts.Ref(self.scale_up_policy)],
    #         Dimensions=[ts.cloudwatch.MetricDimension(
    #             Name='AutoScalingGroupName',
    #             Value=ts.Ref(self.ec2_autoscaling_group),
    #         )],
    #         ComparisonOperator='GreaterThanThreshold',
    #     )
    #
    # @resource
    # def scale_down_policy(self):
    #     return ts.autoscaling.ScalingPolicy(
    #         self._get_logical_id('ScaleDownPolicy'),
    #         AdjustmentType='ChangeInCapacity',
    #         AutoscalingGroupName=ts.Ref(self.ec2_autoscaling_group),
    #         Cooldown=60,
    #         ScalingAdjustment=-1,
    #     )
    #
    # @resource
    # def cpu_alarm_low(self):
    #     return ts.cloudwatch.Alarm(
    #         self._get_logical_id('CPUAlarmLow'),
    #         AlarmDescription='Scale down if CPU < 90% for 10 minutes',
    #         MetricName='CPUUtilization',
    #         Namespace='AWS/EC2',
    #         Statistic='Average',
    #         Period=300,
    #         EvaluationThreshold=2,
    #         Threshold=70,
    #         AlarmActions=[ts.Ref(self.scale_down_policy)],
    #         Dimensions=[ts.cloudwatch.MetricDimension(
    #             Name='AutoScalingGroupName',
    #             Value=ts.Ref(self.ec2_autoscaling_group),
    #         )],
    #         ComparisonOperator='LessThanThreshold',
    #     )

    # service

    @parameter
    def app_image(self):
        return ts.Parameter(
            self._get_logical_id('AppImage'),
            Type='String',
        )

    @app_image.value
    def app_image_value(self):
        return nudge.manager.util.get_latest_image_tag(self.env.config['Ecr']['Repos']['Env']['Url'], *nudge.manager.Component.APP.value)

    @cached_property
    def app_container_def(self):
        return ts.ecs.ContainerDefinition(
            Name='app',
            Image=ts.Ref(self.app_image),
            Cpu=64,
            Memory=256,
            LogConfiguration=nudge.manager.util.aws_logs_config(self.log_group_name),
            Environment=nudge.manager.util.env(
                prefix=ConfigService.ENV_VAR_PREFIX,
                variables={
                     ConfigService.S3_CONFIG_URI: self.s3_config_uri,
                }
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
        return nudge.manager.util.get_latest_image_tag(self.env.config['Ecr']['Repos']['Env']['Url'], *nudge.manager.Component.NGX.value)

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
            LogConfiguration=nudge.manager.util.aws_logs_config(self.log_group_name),
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


    @resource
    def service_role(self):
        return ts.iam.Role(
            self._get_logical_id('ServiceRole'),
            AssumeRolePolicyDocument=awacs.aws.Policy(
                Statement=[awacs.helpers.trust.make_simple_assume_statement('ecs.amazonaws.com')],
            ),
            Path='/',
            Policies=[ts.iam.Policy(
                PolicyName='nudge-web',
                PolicyDocument=awacs.aws.Policy(
                    Statement=[awacs.aws.Statement(
                        Effect='Allow',
                        Action=[
                            awacs.elasticloadbalancing.Action('Describe*'),
                            awacs.elasticloadbalancing.RegisterTargets,
                            awacs.elasticloadbalancing.DeregisterTargets,
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

    @resource_group
    def internal(self):
        return WebService(
            ctx=self._ctx,
            config=self.config['Internal'],
            env=self.env,
            prefix='{}{}'.format(self._prefix, 'Int'),
            authorized_ips=['10.0.0.0/8', '172.16.0.0/12'],  # addresses inside vpc
            service_role=self.service_role,
            task_def=self.task_def,
            cluster=self.ecs_cluster,
            internal=True,
        )

    @resource_group
    def external(self):
        return WebService(
            ctx=self._ctx,
            config=self.config['External'],
            env=self.env,
            prefix='{}{}'.format(self._prefix, 'Ext'),
            authorized_ips=self.authorized_ips,
            service_role=self.service_role,
            task_def=self.task_def,
            cluster=self.ecs_cluster,
            internal=False,
        )


class WebService(ResourceGroup):

    @cached_property
    def vpc_id(self):
        return self.env.vpc_id

    @cached_property
    def elb_name(self):
        return self.config['ElbName']

    @cached_property
    def subnets(self):
        return self.env.subnets

    @cached_property
    def hosted_zone_name(self):
        return self.env.web.hosted_zone_name

    @cached_property
    def target_group_name(self):
        return self.config['TargetGroupName']

    @cached_property
    def record_set_name(self):
        return self.config['RecordSetName']

    @cached_property
    def service_name(self):
        return self.config['ServiceName']

    @cached_property
    def elb_scheme(self):
        return 'internal' if self.is_internal else 'internet-facing'

    def __init__(self, ctx, config, env, prefix, authorized_ips, service_role, task_def, cluster, internal=False):
        super().__init__(ctx, config, prefix=prefix)
        self.env = env
        self.is_internal = internal
        self.authorized_ips = authorized_ips
        self.service_role = service_role
        self.task_def = task_def
        self.cluster = cluster

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
                    DNSName=ts.GetAtt(self.elb, 'DNSName'),
                    HostedZoneId=ts.GetAtt(self.elb, 'CanonicalHostedZoneID'),
                ),
            )],
        )

    @resource
    def security_group(self):
        return ts.ec2.SecurityGroup(
            self._get_logical_id('SecurityGroup'),
            GroupDescription='Nudge Web {type} Elastic Load Balancing Security Group'.format(
                type='Internal' if self.is_internal else 'External',
            ),
            VpcId=self.vpc_id,
            SecurityGroupIngress=[
                ts.ec2.SecurityGroupRule(
                    IpProtocol='tcp',
                    FromPort=80,
                    ToPort=80,
                    CidrIp=ip,
                )
                for ip in self.authorized_ips
            ],
        )

    @resource
    def elb(self):
        return ts.elasticloadbalancingv2.LoadBalancer(
            self._get_logical_id('Elb'),
            Name=self.elb_name,
            Scheme=self.elb_scheme,
            Subnets=self.subnets,
            SecurityGroups=[ts.Ref(self.security_group)],
            # LoadBalancerAttributes=[
            #     ts.elasticloadbalancingv2.LoadBalancerAttributes(Key=k, Value=v)
            #     for k, v in [
            #         ('access_logs.s3.enabled', 'true'),
            #         ('access_logs.s3.bucket', self.config['External']['AccessLogsBucket']),
            #     ]
            # ],
        )

    @resource
    def target_group(self):
        return ts.elasticloadbalancingv2.TargetGroup(
            self._get_logical_id('TargetGroup'),
            Name=self.target_group_name,
            HealthCheckIntervalSeconds=30,
            HealthCheckProtocol='HTTP',
            HealthCheckTimeoutSeconds=10,
            HealthyThresholdCount=4,
            # todo: point to definiiton
            HealthCheckPath='/api/1/call/CheckHealth/',
            Port=8080,
            Protocol='HTTP',
            UnhealthyThresholdCount=4,
            VpcId=self.vpc_id,
        )

    @resource
    def listener(self):
        return ts.elasticloadbalancingv2.Listener(
            self._get_logical_id('Listener'),
            Protocol='HTTP',
            Port=80,
            LoadBalancerArn=ts.Ref(self.elb),
            DefaultActions=[ts.elasticloadbalancingv2.Action(
                Type='forward',
                TargetGroupArn=ts.Ref(self.target_group),
            )],
        )

    @resource
    def service(self):
        return ts.ecs.Service(
            self._get_logical_id('Service'),
            ServiceName=self.service_name,
            Cluster=ts.Ref(self.cluster),
            DesiredCount=2,
            LoadBalancers=[ts.ecs.LoadBalancer(
                # todo: point at definition
                ContainerName='nginx',
                ContainerPort=8080,
                TargetGroupArn=ts.Ref(self.target_group),
            )],
            Role=ts.Ref(self.service_role),
            TaskDefinition=ts.Ref(self.task_def),
            DeploymentConfiguration=ts.ecs.DeploymentConfiguration(
                MaximumPercent=200,
                MinimumHealthyPercent=50,
            ),
            DependsOn=[self.listener.title],
        )

    # @resource
    # def autoscaling_role(self):
    #     return ts.iam.Role(
    #         self._get_logical_id('AutoscalingRole'),
    #         AssumeRolePolicyDocument=awacs.aws.Policy(
    #             Statement=[awacs.helpers.trust.make_simple_assume_statement('application-autoscaling.amazonaws.com')],
    #         ),
    #         Path='/',
    #         Policies=[ts.iam.Policy(
    #             PolicyName='service-autoscaling',
    #             PolicyDocument=awacs.aws.Policy(
    #                 Statement=[awacs.aws.Statement(
    #                     Effect='Allow',
    #                     Action=[
    #                         awacs.application_autoscaling.Action('*'),
    #                         awacs.cloudwatch.DescribeAlarms,
    #                         awacs.cloudwatch.PutMetricAlarm,
    #                         awacs.ecs.DescribeServices,
    #                         awacs.ecs.UpdateService,
    #                     ],
    #                     Resource=['*'],
    #                 )],
    #             ),
    #         )],
    #     )
    #
    # @resource
    # def scaling_target(self):
    #     return ts.applicationautoscaling.ScalableTarget(
    #         self._get_logical_id('ScalingTarget'),
    #         DependsOn=[self.service.title],
    #         MaxCapacity=2,
    #         MinCapacity=1,
    #         ResourceId=ts.Join('', ['service/', ts.Ref(self.cluster), '/', ts.GetAtt(self.service, 'Name')]),
    #         RoleARN=ts.GetAtt(self.autoscaling_role, 'Arn'),
    #         ScalableDimension='ecs:service:DesiredCount',
    #         ServiceNamespace='ecs',
    #     )
    #
    # @resource
    # def scaling_policy(self):
    #     return ts.applicationautoscaling.ScalingPolicy(
    #         self._get_logical_id('ScalingPolicy'),
    #         PolicyName='nudge-scaling-policy',
    #         PolicyType='StepScaling',
    #         ScalingTargetId=ts.Ref(self.scaling_target),
    #         StepScalingPolicyConfiguration=ts.applicationautoscaling.StepScalingPolicyConfiguration(
    #             AdjustmentType='PercentChangeInCapacity',
    #             Cooldown=60,
    #             MetricAggregationType='Average',
    #             StepAdjustments=[ts.applicationautoscaling.StepAdjustment(
    #                 MetricIntervalLowerBound=0,
    #                 ScalingAdjustment=200,
    #             )],
    #         ),
    #     )
