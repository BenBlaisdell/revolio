from flask import json


class DeferralSrv:

    def __init__(self, app, sqs, queue_url):
        super().__init__()
        self._app = app
        self._sqs = sqs
        self._queue_url = queue_url

    def __call__(self, func, *args, **kwargs):
        self._sqs.send_message(
            QueueUrl=self._queue_url,
            MessageBody=json.dumps({
                'Url': self._app.get_url(func),
                'Body': func.format_request(*args, **kwargs),
            }),
        )
