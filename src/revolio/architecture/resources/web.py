import abc
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
import troposphere.ec2
import troposphere.ecs
import troposphere.elasticloadbalancingv2
import troposphere.iam
import troposphere.logs
import troposphere.route53

from revolio.architecture.resources.ecs import EcsResources
from revolio.architecture.stack import resource, resource_group, ResourceGroup


class WebResources(EcsResources):

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
    def log_group_name(self):
        return self._config['LogGroupName']

    def __init__(self, ctx, env):
        super().__init__(ctx, env.config['Web'], env, prefix='Web')

    @resource
    def log_group(self):
        return ts.logs.LogGroup(
            self._get_logical_id('LogGroup'),
            LogGroupName=self.log_group_name,
            RetentionInDays=14,
        )

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

    @cached_property
    def s3_config_uri(self):
        return f's3://{self.env.secrets.bucket_name}/{self.env.secrets.config_key}'

    @cached_property
    def secrets_key_arn(self):
        return ts.GetAtt(self.env.secrets.key, 'Arn')

    @cached_property
    def secrets_bucket(self):
        return self.env.secrets.bucket

    @property
    def profile_role_statements(self):
        return collections.ChainMap(
            {
                # allow pulling s3 config
                'access-secrets-bucket': awacs.aws.Statement(
                    Effect='Allow',
                    Action=[awacs.s3.Action('*')],
                    Resource=[ts.Join('', ['arn:aws:s3:::', ts.Ref(self.secrets_bucket), '*'])],
                ),
                # allow decrypting s3 secrets
                'use-secrets-kms-key': awacs.aws.Statement(
                    Effect='Allow',
                    Action=[awacs.kms.Action('*')],
                    Resource=[self.secrets_key_arn],
                ),
            },
            super().profile_role_statements,
        )

    @property
    @abc.abstractmethod
    def task_def(self):
        pass

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
            prefix=f'{self._prefix}Int',
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
            prefix=f'{self._prefix}Ext',
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
            GroupDescription='{project} Web {type} Elastic Load Balancing Security Group'.format(
                project=self.project_name.capitalize(),
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
            LoadBalancerAttributes=[
                ts.elasticloadbalancingv2.LoadBalancerAttributes(Key=k, Value=v)
                for k, v in [
                    ('access_logs.s3.enabled', 'true'),
                    ('access_logs.s3.bucket', self.config['AccessLogsBucket']),
                ]
            ],
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
            HealthCheckPath='/api/1/call/CheckHealth',
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
