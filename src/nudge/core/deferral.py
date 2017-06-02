from flask import json


class DeferralSrv:

    def __init__(self, log, sqs, def_queue_url):
        super().__init__()
        self._log = log
        self._sqs = sqs
        self._queue_url = def_queue_url

    def send_call(self, func, *args, **kwargs):
        url = func.url
        body = func.format_request(*args, **kwargs)

        self._log.info('Sending deferred call:\n\t{url}\n\t{body}'.format(
            url=url,
            body=body,
        ))

        self._sqs.send_message(
            QueueUrl=self._queue_url,
            MessageBody=json.dumps({
                'Url': url,
                'Body': body,
            }),
        )
