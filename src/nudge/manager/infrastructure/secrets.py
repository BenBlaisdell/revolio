import logging

import awacs.aws
import awacs.kms
import boto3
import botocore.client
import troposphere as ts
import troposphere.cloudformation
import troposphere.kms
import troposphere.policies
import troposphere.s3
from cached_property import cached_property

from revolio.manager.stack import resource, ResourceGroup


class SecretsResources(ResourceGroup):

    @cached_property
    def bucket_name(self):
        return self.config['BucketName']

    @cached_property
    def key_admins(self):
        return self.config['KeyAdmins']

    @cached_property
    def key_name(self):
        return self.config['KeyName']

    @cached_property
    def config_key(self):
        return self.config['ConfigKey']

    def __init__(self, ctx, env):
        super().__init__(ctx, env.config['Secrets'], prefix='Secrets')
        self.env = env

    @resource
    def bucket(self):
        return ts.s3.Bucket(
            self._get_logical_id('Bucket'),
            # DeletionPolicy='Retain',  # do not delete bucket on deletion of stack
            BucketName=self.bucket_name,
        )

    @resource
    def key(self):
        return ts.kms.Key(
            self._get_logical_id('Key'),
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
            self._get_logical_id('KeyAlias'),
            AliasName='alias/{}'.format(self.key_name),
            TargetKeyId=ts.Ref(self.key),
        )

    # @resource
    # def wait_condition_handle(self):
    #     # replace resource each update
    #     normalized_transaction_id = ''.join(self._ctx.transaction_id.split('-')).upper()
    #     return ts.cloudformation.WaitConditionHandle(
    #         self._get_logical_id('WaitConditionHandle{}'.format(normalized_transaction_id)),
    #     )
    #
    # @resource
    # def wait_condition(self):
    #     return ts.cloudformation.WaitCondition(
    #         self._get_logical_id('WaitCondition'),
    #         CreationPolicy=ts.policies.CreationPolicy(
    #             ResourceSignal=ts.policies.ResourceSignal(),
    #         ),
    #         Handle=ts.Ref(self.wait_condition_handle),
    #         Timeout=60*60*12,  # max timout of 12 hours
    #     )
    #
    # @wait_condition.action
    # def upload_config(self):
    #     try:
    #         boto3.client(
    #             service_name='s3',
    #             config=botocore.client.Config(signature_version='s3v4'),
    #         ).put_object(
    #             Bucket=self.bucket_name,
    #             Key=self.config_key,
    #             Body=self.env.ctx.raw_stack_config,
    #             ServerSideEncryption='aws:kms',
    #             SSEKMSKeyId='alias/{}'.format(self.key_name),
    #         )
    #     except Exception as e:
    #         _logger.info('Failed to upload config: {}'.format(str(e)))
    #         return False
    #
    #     return True
