from cached_property import cached_property

from revolio.architecture.resources.db import DatabaseResources
from revolio.architecture.resources.secrets import SecretsResources
from revolio.architecture.stack import resource_group, ResourceGroup


class Env(ResourceGroup):

    @cached_property
    def zones(self):
        return self.config['AvailabilityZones']

    @cached_property
    def ami(self):
        return self.config['Ec2ImageId']

    @cached_property
    def subnets(self):
        return self.config['Subnets']

    @cached_property
    def availability_zones(self):
        return self.config['AvailabilityZones']

    @cached_property
    def authorized_ips(self):
        return self.config['AuthorizedCidrIps']

    @cached_property
    def vpc_id(self):
        return self.config['VpcId']

    @cached_property
    def key_name(self):
        return self.config['KeyName']

    def __init__(self, ctx, config):
        super().__init__(ctx, config)

    @resource_group
    def secrets(self):
        return SecretsResources(
            ctx=self._ctx,
            env=self,
        )

    @resource_group
    def db_resources(self):
        return DatabaseResources(
            ctx=self._ctx,
            env=self,
        )