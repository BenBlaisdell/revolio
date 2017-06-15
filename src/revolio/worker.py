import functools
import json
import abc
import os
import traceback
import signal

import boto3
from cached_property import cached_property


class Worker(metaclass=abc.ABCMeta):

    def __init__(self, logger):
        super().__init__()
        self._logger = logger

    def run(self):
        signal_received = Wrapper(False)
        partial = functools.partial(_handler, self._logger, signal_received)

        # try to allow for graceful shutdown
        for sig in [signal.SIGTERM, signal.SIGINT]:
            signal.signal(sig, partial)

        self._logger.info('Started worker: %s' % type(self).__name__)
        while not signal_received.value:
            try:
                self._task()
            except Exception:
                self._logger.error(json.dumps(traceback.format_exc()))

    @abc.abstractmethod
    def _task(self):
        pass


class Wrapper(object):
    def __init__(self, value):
        self.value = value


# noinspection PyUnusedLocal
def _handler(logger, signal_received, signum, frame):
    logger.info('Signal received: %s' % signum)
    signal_received.value = True


class SqsWorker(Worker):

    QUEUE_URL_VAR = 'QUEUE_URL'

    @property
    @abc.abstractmethod
    def ENV_VAR_PREFIX(self):
        return 'REVOLIO'

    def get_env_var_name(self, key):
        return '{}_{}'.format(self.ENV_VAR_PREFIX, key)

    def get_env_var(self, key):
        return json.loads(os.environ[self.get_env_var_name(key)])

    @cached_property
    def _queue_url(self):
        return self.get_env_var(SqsWorker.QUEUE_URL_VAR)

    @cached_property
    def _queue_region(self):
        # https://sqs.{region}.amazonaws.com/{account_id}/{name}
        return self._queue_url.split('.', 2)[1]

    @cached_property
    def _sqs_client(self):
        return boto3.client('sqs', region_name=self._queue_region)

    def _get_messages(self):
        self._logger.debug('Polling {} for messages'.format(self._queue_url))
        r = self._sqs_client.receive_message(
            QueueUrl=self._queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
        )

        return r.get('Messages', [])

    def _delete_message(self, receipt):
        self._sqs_client.delete_message(
            QueueUrl=self._queue_url,
            ReceiptHandle=receipt
        )

    def _task(self):
        for msg in self._get_messages():
            self._logger.info('Received message {}'.format(
                json.dumps(msg, sort_keys=True, indent=4, separators=(',', ': ')),
            ))

            try:
                self._handle_message(json.loads(msg['Body']))
                self._logger.debug('Deleting message {}'.format(msg['MessageId']))
                self._delete_message(msg['ReceiptHandle'])
            except:
                self._logger.error('\r'.join([
                    'Error processing message {}'.format(msg['MessageId']),
                    traceback.format_exc(),
                ]))

    @abc.abstractmethod
    def _handle_message(self, msg):
        pass
