import functools
import json
import abc
import traceback
import signal


class Worker(metaclass=abc.ABCMeta):

    def __init__(self, logger):
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
