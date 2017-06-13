import logging

from cached_property import cached_property

import awacs.aws
import awacs.ecr
from revolio.manager.stack import resource, ResourceGroup
import troposphere as ts
import troposphere.ecr


_logger = logging.getLogger(__name__)


class EcrResources(ResourceGroup):

    @cached_property
    def repo_name(self):
        return self.config['Repos']['Env']['Name']

    @cached_property
    def repo_admins(self):
        return self.config['Admins']

    def __init__(self, ctx, config):
        super().__init__(ctx, config, prefix='Ecr')

    @resource
    def repo(self):
        return ts.ecr.Repository(
            self._get_logical_id('Repo'),
            RepositoryName=self.repo_name,
            RepositoryPolicyText=awacs.aws.Policy(
                Version='2012-10-17',
                Statement=[awacs.aws.Statement(
                    Effect='Allow',
                    Principal=awacs.aws.AWSPrincipal(self.repo_admins),
                    Action=[awacs.ecr.Action('*')],
                )],
            ),
        )
