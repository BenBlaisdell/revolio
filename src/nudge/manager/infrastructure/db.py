import itertools

import troposphere as ts
import troposphere.ec2
import troposphere.rds
from cached_property import cached_property

from revolio.manager.stack import resource, parameter, ResourceGroup


class DatabaseResources(ResourceGroup):

    @cached_property
    def db_name(self):
        return self.config['Name']

    @cached_property
    def db_username(self):
        return self.config['Username']

    @cached_property
    def db_identifier(self):
        return self.config['Identifier']

    @cached_property
    def storage_size(self):
        return self.config['StorageSize']

    @cached_property
    def instance_class(self):
        return self.config['InstanceClass']

    def __init__(self, ctx, env):
        super().__init__(ctx, env.config['Database'], prefix='Db')
        self.env = env

    @parameter
    def password(self):
        return ts.Parameter(
            self._get_logical_id('DatabasePassword'),
            Type='String',
            NoEcho=True,  # do not print in aws console
        )

    @password.value
    def password_value(self):
        return self.config['Password']

    @resource
    def subnet_group(self):
        return ts.rds.DBSubnetGroup(
            self._get_logical_id('SubnetGroup'),
            DBSubnetGroupDescription='Nudge RDS DBSubnetGroup',
            SubnetIds=self.env.subnets,
        )

    @resource
    def security_group(self):
        return ts.ec2.SecurityGroup(
            self._get_logical_id('SecurityGroup'),
            GroupDescription='Nudge Rds Security Group',
            VpcId=self.env.vpc_id,
            SecurityGroupIngress=[
                ts.ec2.SecurityGroupRule(
                    IpProtocol='tcp',
                    FromPort=5432,
                    ToPort=5432,
                    CidrIp=ip,
                )
                for ip in itertools.chain(
                    ['10.0.0.0/8', '172.16.0.0/12'],  # addresses inside vpc
                    self.env.authorized_ips,
                )
            ],
        )

    @resource
    def db(self):
        return ts.rds.DBInstance(
            self._get_logical_id('Instance'),
            DeletionPolicy='Retain',  # do not delete db on deletion of stack
            DBName=self.db_name,
            MasterUsername=self.db_username,
            MasterUserPassword=ts.Ref(self.password),
            AllocatedStorage=self.storage_size,
            DBSubnetGroupName=ts.Ref(self.subnet_group),
            AvailabilityZone=self.env.availability_zones[0],
            BackupRetentionPeriod=7,
            DBInstanceClass=self.instance_class,
            Engine='postgres',
            EngineVersion='9.6.2',
            LicenseModel='postgresql-license',
            MultiAZ=False,
            Port=5432,
            PreferredBackupWindow='09:00-09:30',
            PreferredMaintenanceWindow='sat:09:31-sat:10:01',
            VPCSecurityGroups=[ts.Ref(self.security_group)],
            PubliclyAccessible=True,
        )
