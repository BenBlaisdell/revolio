import awacs.aws
import awacs.kms
import itertools
import troposphere as ts
import troposphere.ec2
import troposphere.rds
from cached_property import cached_property

from nudge.manager.stack import resource, parameter, ResourceGroup


class DatabaseResources(ResourceGroup):

    @cached_property
    def name(self):
        return self._config['DatabaseName']

    @cached_property
    def username(self):
        return self._config['Username']

    @cached_property
    def storage(self):
        return self._config['StorageSize']

    @cached_property
    def subnets(self):
        return self._config['Subnets']

    @cached_property
    def availability_zone(self):
        return self._config['AvailabilityZone']

    @cached_property
    def instance_class(self):
        return self._config['InstanceClass']

    @cached_property
    def authorized_ips(self):
        return self._config['AuthorizedCidrIps']

    @cached_property
    def vpc_id(self):
        return self._config['VpcId']

    @cached_property
    def db_identifier(self):
        return self._config['DatabaseIdentifier']

    def __init__(self, config):
        super().__init__(config, prefix='Db')

    @parameter
    def password(self):
        return ts.Parameter(
            'DatabasePassword',
            Type='String',
            NoEcho=True,  # do not print in aws console
        )

    @resource
    def subnet_group(self):
        return ts.rds.DBSubnetGroup(
            self._get_logical_id('SubnetGroup'),
            DBSubnetGroupDescription='Nudge RDS DBSubnetGroup',
            SubnetIds=self.subnets,
        )

    @resource
    def security_group(self):
        return ts.ec2.SecurityGroup(
            self._get_logical_id('SecurityGroup'),
            GroupDescription='Nudge Rds Security Group',
            VpcId=self.vpc_id,
            SecurityGroupIngress=[
                ts.ec2.SecurityGroupRule(
                    IpProtocol='tcp',
                    FromPort=5432,
                    ToPort=5432,
                    CidrIp=ip,
                )
                for ip in itertools.chain(
                    ['10.0.0.0/8', '172.16.0.0/12'],  # addresses inside vpc
                    self.authorized_ips,
                )
            ],
        )

    @resource
    def db(self):
        return ts.rds.DBInstance(
            self._get_logical_id('Instance'),
            DeletionPolicy='Retain',  # do not delete db on deletion of stack
            DBName=self.name,
            MasterUsername=self.username,
            MasterUserPassword=ts.Ref(self.password),
            AllocatedStorage=self.storage,
            DBSubnetGroupName=ts.Ref(self.subnet_group),
            AvailabilityZone=self.availability_zone,
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
