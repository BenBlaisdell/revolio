import json
import logging
import os
import sys

import requests
from cached_property import cached_property
import revolio as rv
import revolio.logging
import revolio.util


_logger = logging.getLogger('nudge')
_logger.setLevel(logging.DEBUG)

# console handler
ch = logging.StreamHandler(stream=sys.stdout)
ch.setLevel(logging.DEBUG)

# formatter
formatter = rv.logging.Formatter()
ch.setFormatter(formatter)

# attach handlers
_logger.addHandler(ch)


class DeferralWorker(rv.SqsWorker):

    ENV_VAR_PREFIX = 'NDG_WRK_DEF'

    def __init__(self):
        super(DeferralWorker, self).__init__(_logger)

    def _handle_message(self, msg):
        url = msg['Url']
        body_obj = msg['Body']

        _logger.info('\r'.join(['Sending deferred call', url, rv.util.log_dumps(body_obj)]))
        r = requests.post(url, json=body_obj)

        if r.status_code != 200:
            raise Exception('Nudge call {} failed with code {}'.format(msg['Url'], r.status_code))


if __name__ == '__main__':
    DeferralWorker().run()
