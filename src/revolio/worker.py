import functools
import json
import abc
import logging
import os
import traceback
import signal

import boto3
from cached_property import cached_property


_log = logging.getLogger(__name__)


class Worker(metaclass=abc.ABCMeta):

    def run(self):
        signal_received = Wrapper(False)
        partial = functools.partial(_handler, signal_received)

        # try to allow for graceful shutdown
        for sig in [signal.SIGTERM, signal.SIGINT]:
            signal.signal(sig, partial)

        _log.info('Started worker: %s' % type(self).__name__)
        while not signal_received.value:
            try:
                self._task()
            except Exception:
                _log.error(json.dumps(traceback.format_exc()))

    @abc.abstractmethod
    def _task(self):
        pass


class Wrapper(object):
    def __init__(self, value):
        self.value = value


# noinspection PyUnusedLocal
def _handler(signal_received, signum, frame):
    _log.info('Signal received: %s' % signum)
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
        _log.debug('Polling {} for messages'.format(self._queue_url))
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
            _log.info('Received message {}'.format(
                json.dumps(msg, sort_keys=True, indent=4, separators=(',', ': ')),
            ))

            try:
                self._handle_message(json.loads(msg['Body']))
                _log.debug('Deleting message {}'.format(msg['MessageId']))
                self._delete_message(msg['ReceiptHandle'])
            except:
                _log.error('\r'.join([
                    'Error processing message {}'.format(msg['MessageId']),
                    traceback.format_exc(),
                ]))

    @abc.abstractmethod
    def _handle_message(self, msg):
        pass
