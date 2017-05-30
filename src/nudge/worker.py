import json
import logging
import os
import traceback

import boto3
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


class SubscriptionWorker(rv.Worker):

    def __init__(self):
        super(SubscriptionWorker, self).__init__(_logger)

    @cached_property
    def _queue_url(self):
        return json.loads(os.environ['NUDGE_NOTIFICATION_QUEUE_URL'])

    @cached_property
    def _queue_region(self):
        # https://sqs.{region}.amazonaws.com/{account_id}/{name}
        return self._queue_url.split('.', 2)[1]

    @cached_property
    def _sqs_client(self):
        return boto3.client('sqs', region_name=self._queue_region)

    @cached_property
    def _nudge_client(self):
        return NudgeClient(
            json.loads(os.environ['NUDGE_HOST']),
            port=json.loads(os.environ['NUDGE_PORT']),
            api_version=json.loads(os.environ['NUDGE_VERSION']),
        )

    def _get_messages(self):
        _logger.info('Polling {} for messages'.format(self._queue_url))
        r = self._sqs_client.receive_message(
            QueueUrl=self._queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
        )

        return r.get('Messages', [])

    def _delete_message(self, receipt):
        _logger.info('Deleting message {}'.format(receipt))
        self._sqs_client.delete_message(
            QueueUrl=self._queue_url,
            ReceiptHandle=receipt
        )

    def _send_records(self, msg):
        for record in json.loads(msg['Body']).get('Records', []):
            if 'ObjectCreated' in record['eventName']:
                self._nudge_client.handle_object_created(
                    Bucket=record['s3']['bucket']['name'],
                    Key=record['s3']['object']['key'],
                    Size=record['s3']['object']['size'],
                    Created=record['eventTime']
                )

    def _task(self):
        for msg in self._get_messages():
            _logger.info('Received message {}'.format(msg['MessageId']))

            try:
                self._send_records(msg)
                _logger.info('Deleting message {}'.format(msg['MessageId']))
                self._delete_message(msg['ReceiptHandle'])
            except:
                _logger.error('Error when processing message {id}\n\n{body}\n\n{error}'.format(
                    id=msg['MessageId'],
                    body=msg['Body'],
                    error=json.dumps(traceback.format_exc()),
                ))


if __name__ == '__main__':
    SubscriptionWorker().run()
