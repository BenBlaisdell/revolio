import datetime as dt
import json

from nudge.core.entity import Element


class BatchService:

    def __init__(self, ctx, db):
        self._ctx = ctx
        self._db = db

    def send_batch(self, sub, elems):
        for elem in elems:
            elem.state = Element.State.Sent

        self._db.flush()

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
