import logging
import logging.config

from cached_property import cached_property


class LogService:

    @cached_property
    def _logger(self):
        l = logging.getLogger('nudge')
        l.setLevel(logging.DEBUG)
        l.addHandler(self._handler)
        return l

    @cached_property
    def _handler(self):
        h = logging.StreamHandler()
        h.setLevel(logging.DEBUG)
        h.setFormatter(self._formatter)
        return h

    @cached_property
    def _formatter(self):
        return logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def __init__(self):
        sa_logger = logging.getLogger('sqlalchemy.engine')
        sa_logger.setLevel(logging.INFO)
        sa_logger.addHandler(self._handler)

    def debug(self, *msgs):
        self._log(self._logger.debug, msgs)

    def info(self, *msgs):
        self._log(self._logger.info, msgs)

    def warning(self, *msgs):
        self._log(self._logger.warning, msgs)

    @staticmethod
    def _log(log_func, msgs):
        log_func('\r'.join(msgs))
