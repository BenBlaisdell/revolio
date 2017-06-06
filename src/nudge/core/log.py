import logging
import logging.config


class LogService:

    def __init__(self):
        self._logger = logging.getLogger('nudge')
        self._logger.setLevel(logging.DEBUG)

        # console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

        # formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)

        # attach handlers
        self._logger.addHandler(ch)

    def debug(self, *msgs):
        self._log(self._logger.debug, msgs)

    def info(self, *msgs):
        self._log(self._logger.info, msgs)

    def warning(self, *msgs):
        self._log(self._logger.warning, msgs)

    @staticmethod
    def _log(log_func, msgs):
        log_func('\r'.join(msgs))
