import json

from nudge.entity.element import Element


class BatchService:

    def __init__(self, ctx, db):
        self._ctx = ctx
        self._db = db

    def send_batch(self, sub, elems):
        for elem in elems:
            elem.state = Element.State.Sent

        self._db.flush()

        if sub.custom:
            msg = json.dumps(sub.custom)
        else:
            msg = json.dumps({
                'SubscriptionId': sub.id,
            })

        sub.endpoint.send_message(ctx=self._ctx, msg=msg)
