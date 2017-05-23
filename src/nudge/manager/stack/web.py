import logging

import awacs.aws
import awacs.autoscaling
import awacs.ecs
import awacs.events
import awacs.elasticloadbalancing
import awacs.ec2
import awacs.s3
import awacs.kms
import awacs.helpers.trust
import awacs.logs
import itertools
import troposphere as ts
import troposphere.cloudformation
import troposphere.cloudwatch
import troposphere.autoscaling
import troposphere.ec2
import troposphere.ecs
import troposphere.iam
import troposphere.logs
import troposphere.elasticloadbalancing
import troposphere.route53


import nudge.manager.util


_logger = logging.getLogger(__name__)


def add_resources(t, config):

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
    s3_conf_uri = config['S3ConfigUri']
    secrets_key_arn = config['SecretsKeyArn']
    authorized_ips = config['AuthorizedCidrIps']

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
        record_set_name, hosted_zone_name, key_name, ami, zones, flask_img, nginx_img, s3_conf_uri,
        secrets_key_arn, authorized_ips,
    )


def _add_web(t, instance_type, vpc_id, subnets, cluster, log_group, record_set_name, hosted_zone_name, key_name, ami,
             zones, flask_img, nginx_img, s3_conf_uri, secrets_key_arn, authorized_ips):

    flask_container_name = 'flask'
    task_def = t.add_resource(ts.ecs.TaskDefinition(
        'WebTaskDefinition',
        ContainerDefinitions=[
            ts.ecs.ContainerDefinition(
                Name=flask_container_name,
                Image=nudge.manager.util.get_latest_image_tag(flask_img),
                Cpu=64,
                Memory=256,
                PortMappings=[ts.ecs.PortMapping(
                    HostPort=9091,
                    ContainerPort=9091,
                )],
                LogConfiguration=_aws_logs_config('web', 'flask'),
                Environment=[ts.ecs.Environment(
                    Name='S3_CONFIG_URI',
                    Value=s3_conf_uri,
                )],
            ),
            ts.ecs.ContainerDefinition(
                Name='nginx',
                Image=nudge.manager.util.get_latest_image_tag(nginx_img),
                Cpu=64,
                Memory=256,
                PortMappings=[ts.ecs.PortMapping(
                    HostPort=8080,
                    ContainerPort=8080,
                )],
                LogConfiguration=_aws_logs_config('web', 'nginx'),
                VolumesFrom=[ts.ecs.VolumesFrom(SourceContainer=flask_container_name)],
            ),
        ],
    ))

    elb, s_group = _add_web_load_balancing(t, vpc_id, subnets, record_set_name, hosted_zone_name, authorized_ips)

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
                    'access-s3-resources',  # allow pulling s3 config
                    awacs.aws.Statement(
                        Effect='Allow',
                        Action=[awacs.s3.Action('*')],
                        Resource=[
                            'arn:aws:s3:::{}*'.format(nudge.manager.util.get_bucket(s3_conf_uri)),
                        ],
                    ),
                ), (
                    'use-secrets-kms-key',  # allow decrypting s3 secrets
                    awacs.aws.Statement(
                        Effect='Allow',
                        Action=[awacs.kms.Action('*')],
                        Resource=[secrets_key_arn],
                    ),
                ), (
                    'ecs',  # register instance in cluster
                    awacs.aws.Statement(
                        Effect='Allow',
                        Action=[awacs.ecs.Action('*')],
                        Resource=['*'],
                    ),
                ), (
                    'logs',  # publish container logs to log group
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
    ))

    instance_profile = t.add_resource(ts.iam.InstanceProfile(
        'WebInstanceProfile',
        Path='/',
        Roles=[ts.Ref(instance_profile_role)],
    ))

    ecs_service = t.add_resource(ts.ecs.Service(
        'WebEcsService',
        Cluster=ts.Ref(cluster),
        DesiredCount=2,
        LoadBalancers=[ts.ecs.LoadBalancer(
            ContainerName='nginx',
            ContainerPort=8080,
            LoadBalancerName=ts.Ref(elb),
        )],
        Role=ts.Ref(service_role),
        TaskDefinition=ts.Ref(task_def),
    ))

    asg_logical_id = 'WebAutoscalingGroup'
    launch_config_logical_id = 'WebLaunchConfiguration'

    launch_config = t.add_resource(ts.autoscaling.LaunchConfiguration(
        launch_config_logical_id,
        KeyName=key_name,
        ImageId=ami,
        AssociatePublicIpAddress=True,
        SecurityGroups=[ts.Ref(s_group)],
        IamInstanceProfile=ts.Ref(instance_profile),
        InstanceType=instance_type,
        Metadata=ts.autoscaling.Metadata(
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
                                'path=Resources.{}.Metadata.AWS::CloudFormation::Init'.format(launch_config_logical_id), '\n',
                                'action=/opt/aws/bin/cfn-init -v ',
                                '    --stack    ', ts.Ref('AWS::StackName'),
                                '    --resource ', launch_config_logical_id,
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
                            'echo ECS_CLUSTER=', ts.Ref(cluster), ' >> /etc/ecs/ecs.config',
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
        ),
        UserData=ts.Base64(ts.Join('', [
            '#!/bin/bash -xe', '\n',
            'yum install -y aws-cfn-bootstrap', '\n',
            '/opt/aws/bin/cfn-init -v ',
            '    --stack    ', ts.Ref('AWS::StackName'),
            '    --resource ', launch_config_logical_id,
            '    --region   ', ts.Ref('AWS::Region'),
            '\n',
            '/opt/aws/bin/cfn-signal -e $? ',
            '     --stack   ', ts.Ref('AWS::StackName'),
            '    --resource ', asg_logical_id,
            '    --region   ', ts.Ref('AWS::Region'),
            '\n',
        ])),
    ))

    asg = t.add_resource(ts.autoscaling.AutoScalingGroup(
        asg_logical_id,
        LaunchConfigurationName=ts.Ref(launch_config),
        VPCZoneIdentifier=subnets,
        AvailabilityZones=zones,
        MinSize=2,
        MaxSize=5,
        HealthCheckType='ELB',
        HealthCheckGracePeriod=900,
        LoadBalancerNames=[ts.Ref(elb)],
    ))


def _aws_logs_config(service, container):
    return ts.ecs.LogConfiguration(
        LogDriver='awslogs',
        Options={
            'awslogs-group': 'dwh-nudge',
            'awslogs-region': 'us-east-1',
            'awslogs-stream-prefix': '{}/{}'.format(service, container),
        },
    )

def _add_web_load_balancing(t, vpc_id, subnets, record_set_name, hosted_zone_name, authorized_ips):
    security_group = t.add_resource(ts.ec2.SecurityGroup(
        'WebSecurityGroup',
        GroupDescription='Nudge Web Security Group',
        VpcId=vpc_id,
        SecurityGroupIngress=[
            ts.ec2.SecurityGroupRule(
                IpProtocol='tcp',
                FromPort=lower,
                ToPort=upper,
                CidrIp=ip,
            )
            for lower, upper in [(80, 8080), (22, 22)]
            for ip in itertools.chain(
                ['10.0.0.0/8', '172.16.0.0/12'],
                authorized_ips,
            )
        ],
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


def _container_def(image, service, container, port, log_group, env=None, cpu=64, memory=256):
    return ts.ecs.ContainerDefinition(
        Name=container,
        Image=nudge.manager.util.get_latest_image_tag(image),
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
        Environment=env or [],
    )
