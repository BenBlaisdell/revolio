import json
import logging

import revolio as rv
import revolio.util.str


_log = logging.getLogger(__name__)


class DeferralSrv:

    def __init__(self, sqs, def_queue_url):
        super().__init__()
        self._sqs = sqs
        self._queue_url = def_queue_url

    def send_call(self, func, *args, **kwargs):
        url = func.internal_url
        body = func.format_request(*args, **kwargs)

        _log.info('\r'.join([
            'Sending deferred call:',
            url,
            rv.util.str.log_dumps(body),
        ]))

        self._sqs.send_message(
            QueueUrl=self._queue_url,
            MessageBody=json.dumps({
                'Url': url,
                'Body': body,
            }),
        )
