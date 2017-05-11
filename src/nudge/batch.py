import datetime as dt

import json


class BatchService:

    def __init__(self, ctx):
        self._ctx = ctx

    def send_batch(self, sub, elems):
        msg = json.dumps({
            'SubscriptionId': sub.id,
            'Elements': [
                {
                    'Id': elem.id,
                    'Bucket': elem.bucket,
                    'Key': elem.key,
                    'Size': elem.size,
                    'Created': dt.datetime.strftime(elem.created, '%Y-%m-%d %H:%M:%S'),
                }
                for elem in elems
            ],
        })

        sub.endpoint.send_message(ctx=self._ctx, msg=msg)
