import awacs.aws
import awacs.kms
import troposphere as ts
import troposphere.s3
import troposphere.kms
from cached_property import cached_property

from nudge.manager.stack import resource, ResourceGroup


class S3Resources(ResourceGroup):

    @cached_property
    def bucket_name(self):
        return self._config['BucketName']

    @cached_property
    def key_admins(self):
        return self._config['KeyAdmins']

    @cached_property
    def key_name(self):
        return self._config['KeyName']

    def __init__(self, config):
        super().__init__(config, prefix='S3')

    @resource
    def bucket(self):
        return ts.s3.Bucket(
            'Bucket',
            DeletionPolicy='Retain',  # do not delete bucket on deletion of stack
            BucketName=self.bucket_name,
        )

    @resource
    def key(self):
        return ts.kms.Key(
            self._get_logical_id('SecretsKey'),
            KeyPolicy=awacs.aws.Policy(
                Statement=[awacs.aws.Statement(
                    Principal=awacs.aws.AWSPrincipal(self.key_admins),
                    Effect='Allow',
                    Action=[awacs.kms.Action('*')],
                    Resource=['*'],
                )],
            ),
        )

    @resource
    def key_alias(self):
        return ts.kms.Alias(
            self._get_logical_id('SecretsKeyAlias'),
            AliasName='alias/{}'.format(self.key_name),
            TargetKeyId=ts.Ref(self.key),
        )
