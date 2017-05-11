import json


class BatchService:

    def __init__(self, ctx):
        self._ctx = ctx

    def send_batch(self, sub, elems):
        msg = json.dumps({
            'SubscriptionId': sub.id,
            'Elements': [elem.serialize() for elem in elems],
        })

        sub.endpoint.send_message(self._ctx, msg=msg)
