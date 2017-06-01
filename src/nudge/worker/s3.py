import json
import logging
import os
import sys

from cached_property import cached_property
import revolio as rv

from nudge.core.client import NudgeClient


_logger = logging.getLogger('nudge')
_logger.setLevel(logging.DEBUG)

# console handler
ch = logging.StreamHandler(stream=sys.stdout)
ch.setLevel(logging.DEBUG)

# formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

# attach handlers
_logger.addHandler(ch)


class S3EventsWorker(rv.SqsWorker):

    env_var_prefix = 'NDG_WRK_S3E'

    def __init__(self):
        super(S3EventsWorker, self).__init__(_logger)

    @cached_property
    def _nudge_client(self):
        return NudgeClient(
            self.get_env_var('HOST'),
            port=self.get_env_var('PORT'),
            api_version=self.get_env_var('VERSION'),
        )

    def _handle_message(self, msg):
        for record in json.loads(msg['Body']).get('Records', []):
            if 'ObjectCreated' in record['eventName']:
                self._nudge_client.handle_object_created(
                    Bucket=record['s3']['bucket']['name'],
                    Key=record['s3']['object']['key'],
                    Size=record['s3']['object']['size'],
                    Created=record['eventTime']
                )


if __name__ == '__main__':
    S3EventsWorker().run()
