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
    def app_repo_name(self):
        return self.config['Repos']['Web']['App']['Name']

    @cached_property
    def nginx_repo_name(self):
        return self.config['Repos']['Web']['Ngx']['Name']

    @cached_property
    def s3e_worker_repo_name(self):
        return self.config['Repos']['Wrk']['S3e']['Name']

    @cached_property
    def def_worker_repo_name(self):
        return self.config['Repos']['Wrk']['Def']['Name']

    @cached_property
    def repo_admins(self):
        return self.config['Admins']

    def __init__(self, ctx, config):
        super().__init__(ctx, config, prefix='Ecr')

    def _get_repo_policy(self):
        return awacs.aws.Policy(
            Version='2012-10-17',
            Statement=[awacs.aws.Statement(
                Effect='Allow',
                Principal=awacs.aws.AWSPrincipal(self.repo_admins),
                Action=[awacs.ecr.Action('*')],
            )],
        )

    @resource
    def app_repo(self):
        return ts.ecr.Repository(
            self._get_logical_id('WebAppRepo'),
            RepositoryName=self.app_repo_name,
            RepositoryPolicyText=self._get_repo_policy(),
        )

    @resource
    def nginx_repo(self):
        return ts.ecr.Repository(
            self._get_logical_id('WebNgxRepo'),
            RepositoryName=self.nginx_repo_name,
            RepositoryPolicyText=self._get_repo_policy(),
        )

    @resource
    def s3_events_repo(self):
        return ts.ecr.Repository(
            self._get_logical_id('WrkS3eRepo'),
            RepositoryName=self.s3e_worker_repo_name,
            RepositoryPolicyText=self._get_repo_policy(),
        )

    @resource
    def deferral_repo(self):
        return ts.ecr.Repository(
            self._get_logical_id('WrkDefRepo'),
            RepositoryName=self.def_worker_repo_name,
            RepositoryPolicyText=self._get_repo_policy(),
        )
