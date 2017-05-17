import logging
import os
import json
import traceback

from nudge.worker.worker import Worker
from nudge.context import NudgeContext
from nudge.endpoint import SqsEndpoint
from nudge.client.nudge import NudgeClient

_logger = logging.getLogger()

class SubscriptionWorker(Worker):
    def __init__(self):
        super(SubscriptionWorker, self).__init__(_logger)
        config_uri = os.environ['S3_CONFIG_URI']
        self._ctx = NudgeContext(config_uri)

        queue_url = os.environ['ENDPOINT_QUEUE_URL']
        self._queue = SqsEndpoint(queue_url)

        host = os.environ['NUDGE_HOST']
        port = os.environ['NUDGE_PORT']
        version = os.environ['NUDGE_VERSION']
        self._nudge_client = NudgeClient(host, port=port, api_version=version)

    def _task(self):
        messages = self._queue.receive_message(self._ctx) or []
        for sqs_message in messages:
            _logger.info('Received message {message_id}'.format(message_id=sqs_message['MessageId']))
            try:
                message = json.loads(sqs_message['Body'])
                for record in message.get('Records', []):
                    if 'ObjectCreated' in record['eventName']:
                        self._nudge_client.handle_object_created(
                            Bucket=record['s3']['bucket']['name'],
                            Key=record['s3']['object']['key'],
                            Size=record['s3']['object']['size'],
                            Created=record['eventTime'])
            _logger.info('Deleting message {message_id}'.format(message_id=sqs_message['MessageId']))
            self._queue.delete_message(self._ctx, sqs_message['ReceiptHandle'])
            except Exception as e:
                _logger.error('Error when processing message {message}\n\n\n{error}'.format(
                    message=sqs_message['Body'],
                    error=json.dumps(traceback.format_exc())
                ))

if __name__ == 'main':
    worker = SubscriptionWorker()
    worker()