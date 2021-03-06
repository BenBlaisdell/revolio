import logging

import requests

import revolio as rv
import revolio.util.str
import revolio.worker

import nudge


_log = logging.getLogger(__name__)


class DeferralWorker(rv.worker.SqsWorker):

    ENV_VAR_PREFIX = 'NDG_WRK_DEF'

    def __init__(self):
        super(DeferralWorker, self).__init__(nudge.__name__)

    def _handle_message(self, msg):
        url = msg['Url']
        body_obj = msg['Body']

        _log.info('\r'.join(['Sending deferred call', url, rv.util.str.log_dumps(body_obj)]))
        r = requests.post(url, json=body_obj)

        if r.status_code != 200:
            raise Exception(f'Nudge call {url} failed with code {r.status_code}')


if __name__ == '__main__':
    DeferralWorker().run()
