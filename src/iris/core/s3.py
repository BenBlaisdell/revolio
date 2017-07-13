import contextlib
import logging

import boto3
import box

from cached_property import cached_property


_log = logging.getLogger(__name__)


class S3:

    def __init__(self):
        super().__init__()

    def __getattr__(self, item):
        return getattr(self._client, item)

    @cached_property
    def _client(self):
        return boto3.client('s3')

    @contextlib.contextmanager
    def topic_notification_configs(self, bucket):
        with self.notification_configs(bucket) as configs:
            yield configs['TopicConfigurations']

    @contextlib.contextmanager
    def notification_configs(self, bucket):
        configs = self._get_notification_configs(bucket)
        yield configs
        self._put_notification_configs(bucket, configs)

    def _get_notification_configs(self, bucket):
        b_notification = self._client.get_bucket_notification_configuration(
            Bucket=bucket,
        )

        n_configs = {
            config_type: {c['Id']: c for c in b_notification.get(config_type, [])}
            for config_type in (
                'TopicConfigurations',
                'QueueConfigurations',
                'LambdaFunctionConfigurations',
            )
        }

        _log.debug(f'Retrieved notification configs for {bucket}:\r{n_configs}')
        return n_configs

    def _put_notification_configs(self, bucket, configs):
        configs = {
            c_type: tuple(c.values())
            for c_type, c in configs.items()
            if (c is not None) and (len(c) > 0)
        }

        _log.debug(f'Putting notification configs on {bucket}:\r{configs}')
        self._client.put_bucket_notification_configuration(
            Bucket=bucket,
            NotificationConfiguration=configs,
        )
