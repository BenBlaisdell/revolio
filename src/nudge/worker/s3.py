import datetime as dt
import json
import logging
import os
import sys

from cached_property import cached_property
import revolio as rv
import revolio.logging

import nudge
from nudge.core.client import NudgeClient


_log = logging.getLogger(__name__)


class S3EventsWorker(rv.SqsWorker):

    ENV_VAR_PREFIX = 'NDG_WRK_S3E'

    HOST_VAR = 'HOST'
    PORT_VAR = 'PORT'
    VERSION_VAR = 'VERSION'

    def __init__(self):
        super(S3EventsWorker, self).__init__(nudge.__name__)

    @cached_property
    def _nudge_client(self):
        return NudgeClient(
            self.get_env_var(S3EventsWorker.HOST_VAR),
            port=self.get_env_var(S3EventsWorker.PORT_VAR),
            api_version=self.get_env_var(S3EventsWorker.VERSION_VAR),
        )

    def _handle_message(self, msg):
        # if msg['Event'] == 's3:TestEvent':
        #     _log.info('Received test event message for bucket {}'.format(msg['Bucket']))
        #     return

        # extract s3 notification if receiving from sns
        if msg.get('Type') == 'Notification':
            msg = json.loads(msg['Message'])

        for record in msg.get('Records', []):
            if 'ObjectCreated' in record['eventName']:

                bucket = record['s3']['bucket']['name']
                key = record['s3']['object']['key']
                size = record['s3']['object']['size']
                # remove milliseconds and add space between date and time
                created = record['eventTime'][:-len('.000Z')].replace('T', ' ')

                _log.info(f'Sending S3 object s3://{bucket}/{key}')

                self._nudge_client.handle_object_created(
                    Bucket=bucket,
                    Key=key,
                    Size=size,
                    Created=created,
                )


if __name__ == '__main__':
    S3EventsWorker().run()
