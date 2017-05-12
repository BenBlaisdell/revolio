import logging


class LogService:

    def __init__(self):
        self._logger = logging.getLogger()

    def debug(self, msg):
        self._logger.debug(msg)

    def info(self, msg):
        self._logger.info(msg)

    def warning(self, msg):
        self._logger.warning(msg)
