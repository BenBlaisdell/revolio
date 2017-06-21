import functools
import json
import abc
import logging
import os
import traceback
import signal
import uuid

import boto3
from cached_property import cached_property

import revolio as rv
import revolio.logging


_log = logging.getLogger(__name__)


class Worker(metaclass=abc.ABCMeta):

    def __init__(self, namespace):
        super().__init__()
        self._transaction_id = None

        handler = logging.StreamHandler()
        handler.addFilter(rv.logging.WorkerRequestIdFilter(self))
        handler.setLevel(logging.DEBUG)

        for name in [namespace, revolio.__name__, 'sqlalchemy.engine']:
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
            logger.addHandler(handler)

    @property
    def transaction_id(self):
        return self._transaction_id

    def run(self):
        signal_received = Wrapper(False)
        partial = functools.partial(_handler, signal_received)

        # try to allow for graceful shutdown
        for sig in [signal.SIGTERM, signal.SIGINT]:
            signal.signal(sig, partial)

        _log.info('Started worker: %s' % type(self).__name__)
        while not signal_received.value:
            try:
                self._transaction_id = str(uuid.uuid4())
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
        return f'{self.ENV_VAR_PREFIX}_{key}'

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
            pretty_msg = json.dumps(msg, sort_keys=True, indent=4, separators=(',', ': '))
            _log.info(f'Received message {pretty_msg}')

            m_id = msg['MessageId']
            body = msg['Body']

            try:
                self._handle_message(json.loads(body))
                _log.debug(f'Deleting message {m_id}')
                self._delete_message(msg['ReceiptHandle'])
            except:
                _log.error('\r'.join([
                    f'Error processing message {m_id}',
                    traceback.format_exc(),
                ]))
                raise

    @abc.abstractmethod
    def _handle_message(self, msg):
        pass
