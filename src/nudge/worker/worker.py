import functools
import json
import abc
import traceback
import signal


class Worker(object):
    def __init__(self, logger):
        self.logger = logger

    def __call__(self):
        signal_received = Wrapper(False)
        partial = functools.partial(_handler, self.logger, signal_received)

        # try to allow for graceful shutdown
        for sig in [signal.SIGTERM, signal.SIGINT]:
            signal.signal(sig, partial)

        self.logger.info('started worker: %s' % type(self).__name__)
        while not signal_received.value:
            try:
                self._task()

            except Exception:
                self.logger.error(json.dumps(traceback.format_exc()))

    @abc.abstractmethod
    def _task(self):
        NotImplementedError


class Wrapper(object):
    def __init__(self, value):
        self.value = value


# noinspection PyUnusedLocal
def _handler(logger, signal_received, signum, frame):
    logger.info('signal received: %s' % signum)
    signal_received.value = True
