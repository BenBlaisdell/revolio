import logging
import os

import awacs.aws
import awacs.autoscaling
import awacs.events
import awacs.elasticloadbalancing
import awacs.ec2
import awacs.helpers.trust
import troposphere as ts
import troposphere.cloudwatch
import troposphere.autoscaling
import troposphere.ec2
import troposphere.ecs
import troposphere.iam
import troposphere.logs
import troposphere.elasticloadbalancing
import troposphere.route53


_logger = logging.getLogger(__name__)


def build_template(ctx):
    config = ctx.architecture_config

    vpc = config['VpcId']
    subnets = config['Subnets']
    ami = config['Ec2ImageId']
    zones = config['AvailabilityZones']
    record_set_name = config['RecordSetName']
    hosted_zone_name = config['HostedZoneName']
    key_name = config['KeyName']
    web_i_type = config['WebInstanceType']
    flask_img = config['FlaskImage']
    nginx_img = config['NginxImage']

    t = ts.Template()

    # resources

    l_group = t.add_resource(ts.logs.LogGroup(
        'LogGroup',
        LogGroupName='dwh-nudge',
        RetentionInDays=14,
    ))

    cluster = t.add_resource(ts.ecs.Cluster(
        'EcsCluster',
        ClusterName='nudge',
    ))

    _add_web(
        t, web_i_type, vpc, subnets, cluster, l_group,
        record_set_name, hosted_zone_name, key_name, ami, zones, flask_img, nginx_img,
    )

    ctx.save_template(t.to_json())


def _add_web(t, instance_type, vpc_id, subnets, cluster, log_group,
             record_set_name, hosted_zone_name, key_name, ami, zones, flask_img, nginx_img,):

    task_def = t.add_resource(ts.ecs.TaskDefinition(
        'WebTaskDefinition',
        ContainerDefinitions=[
            _container_def(flask_img, 'web', 'flask', 9091, log_group),
            _container_def(nginx_img, 'web', 'nginx', 8080, log_group),
        ],
    ))

    elb, s_group = _add_web_load_balancing(t, vpc_id, subnets, record_set_name, hosted_zone_name)

    service_role = t.add_resource(ts.iam.Role(
        'WebServiceRole',
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
    ))

    instance_profile_role = t.add_resource(ts.iam.Role(
        'WebInstanceProfileRole',
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
                    'events',
                    awacs.aws.Statement(
                        Effect='Allow',
                        Action=[awacs.events.Action('*')],
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
    ))

    instance_profile = t.add_resource(ts.iam.InstanceProfile(
        'WebInstanceProfile',
        Path='/',
        Roles=[ts.Ref(instance_profile_role)],
    ))

    ecs_service = t.add_resource(ts.ecs.Service(
        'WebEcsService',
        Cluster=ts.Ref(cluster),
        DesiredCount=0,
        LoadBalancers=[ts.ecs.LoadBalancer(
            ContainerName='nginx',
            ContainerPort=8080,
            LoadBalancerName=ts.Ref(elb),
        )],
        Role=ts.Ref(service_role),
        TaskDefinition=ts.Ref(task_def),
    ))

    t.add_resource(ts.ec2.Instance(
        'WebInstance',
        ImageId=ami,
        InstanceType=instance_type,
        IamInstanceProfile=ts.Ref(instance_profile),
        SecurityGroups=[ts.Ref(s_group)],
        PlacementGroupName=ts.Ref(cluster),
    ))

    # launch_config = t.add_resource(ts.autoscaling.LaunchConfiguration(
    #     'WebLaunchConfiguration',
    #     KeyName=key_name,
    #     ImageId=ami,
    #     AssociatePublicIpAddress=True,
    #     SecurityGroups=[ts.Ref(s_group)],
    #     IamInstanceProfile=ts.Ref(instance_profile),
    #     InstanceType=instance_type,
    # ))
    #
    # asg = t.add_resource(ts.autoscaling.AutoScalingGroup(
    #     'WebAutoscalingGroup',
    #     LaunchConfigurationName=ts.Ref(launch_config),
    #     VPCZoneIdentifier=subnets,
    #     AvailabilityZones=zones,
    #     MinSize=2,
    #     MaxSize=5,
    #     HealthCheckType='ELB',
    #     HealthCheckGracePeriod=900,
    #     LoadBalancerNames=[ts.Ref(elb)],
    # ))


def _add_web_load_balancing(t, vpc_id, subnets, record_set_name, hosted_zone_name):
    security_group = t.add_resource(ts.ec2.SecurityGroup(
        'WebSecurityGroup',
        GroupDescription='Nudge Web Security Group',
        VpcId=vpc_id,
        SecurityGroupIngress=[
            ts.ec2.SecurityGroupRule(
                IpProtocol='tcp',
                FromPort=80,
                ToPort=80,
                CidrIp=ip,
            )
            for ip in ['10.0.0.0/8', '172.16.0.0/12']
        ]
    ))

    elb = t.add_resource(ts.elasticloadbalancing.LoadBalancer(
        'WebElb',
        CrossZone=True,
        Scheme='internet-facing',
        Subnets=subnets,
        SecurityGroups=[ts.Ref(security_group)],
        Listeners=[ts.elasticloadbalancing.Listener(
            LoadBalancerPort=80,
            InstancePort=8080,
            Protocol='HTTP',
            PolicyNames=['NudgeWebVersionCookieStickinessPolicy'],
        )],
        HealthCheck=ts.elasticloadbalancing.HealthCheck(
            Target='HTTP:8080/',
            HealthyThreshold=2,
            UnhealthyThreshold=7,
            Interval=30,
            Timeout=10,
        ),
        ConnectionDrainingPolicy=ts.elasticloadbalancing.ConnectionDrainingPolicy(
            Enabled=True,
            Timeout=300,
        ),
        AppCookieStickinessPolicy=[ts.elasticloadbalancing.AppCookieStickinessPolicy(
            CookieName='nudge.web.version',
            PolicyName='NudgeWebVersionCookieStickinessPolicy',
        )],
    ))

    t.add_resource(ts.route53.RecordSetGroup(
        'WebElbRecordSetGroup',
        HostedZoneName=hosted_zone_name,
        RecordSets=[ts.route53.RecordSet(
            Name=record_set_name,
            Type='A',
            AliasTarget=ts.route53.AliasTarget(
                EvaluateTargetHealth=False,
                DNSName=ts.GetAtt(elb, 'CanonicalHostedZoneName'),
                HostedZoneId=ts.GetAtt(elb, 'CanonicalHostedZoneNameID'),
            ),
        )],
    ))

    return elb, security_group


def _add_web_scaling(t, asg):
    _add_web_scale_up(t, asg)
    _add_web_scale_down(t, asg)


def _add_web_scale_up(t, asg):
    scale_policy = t.add_resource(ts.autoscaling.ScalingPolicy(
        'WebScaleUpPolicy',
        AdjustmentType='ChangeInCapacity',
        AutoscalingGroupName=ts.Ref(asg),
        Cooldown=60,
        ScalingAdjustment=1,
    ))

    t.add_resource(ts.cloudwatch.Alarm(
        'WebCPUAlarmHigh',
        AlarmDescription='Scale up if CPU > 90% for 10 minutes',
        MetricName='CPUUtilization',
        Namespace='AWS/EC2',
        Statistic='Average',
        Period=300,
        EvaluationThreshold=2,
        Threshold=90,
        AlarmActions=[ts.Ref(scale_policy)],
        Dimensions=[ts.cloudwatch.MetricDimension(
            Name='AutoScalingGroupName',
            Value=ts.Ref(asg),
        )],
        ComparisonOperator='GreaterThanThreshold',
    ))


def _add_web_scale_down(t, asg):
    scale_policy = t.add_resource(ts.autoscaling.ScalingPolicy(
        'WebScaleDownPolicy',
        AdjustmentType='ChangeInCapacity',
        AutoscalingGroupName=ts.Ref(asg),
        Cooldown=60,
        ScalingAdjustment=-1,
    ))

    t.add_resource(ts.cloudwatch.Alarm(
        'WebCPUAlarmLow',
        AlarmDescription='Scale down if CPU < 90% for 10 minutes',
        MetricName='CPUUtilization',
        Namespace='AWS/EC2',
        Statistic='Average',
        Period=300,
        EvaluationThreshold=2,
        Threshold=70,
        AlarmActions=[ts.Ref(scale_policy)],
        Dimensions=[ts.cloudwatch.MetricDimension(
            Name='AutoScalingGroupName',
            Value=ts.Ref(asg),
        )],
        ComparisonOperator='LessThanThreshold',
    ))


def _container_def(image, service, container, port, log_group, cpu=64, memory=256):
    return ts.ecs.ContainerDefinition(
        Name=container,
        Image=image,
        Cpu=cpu,
        Memory=memory,
        PortMappings=[ts.ecs.PortMapping(
            HostPort=port,
            ContainerPort=port,
        )],
        LogConfiguration=ts.ecs.LogConfiguration(
            LogDriver='awslogs',
            Options={
                'awslogs-group': 'dwh-nudge',
                'awslogs-region': 'us-east-1',
                'awslogs-stream-prefix': '{}/{}'.format(service, container),
            },
        ),
    )


def _get_image(service, container):
    return 'image-uri'  # todo
