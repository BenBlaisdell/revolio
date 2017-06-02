import json
import uuid

from nudge.core.entity import Element, Subscription


class BatchService:

    def __init__(self, ctx, db, elem_srv):
        self._ctx = ctx
        self._db = db
        self._elem_srv = elem_srv

    def create_batch(self, sub, elems):
        batch_id = str(uuid.uuid4())
        for elem in elems:
            assert elem.state == Element.State.Unconsumed
            assert elem.sub_id == sub.id
            elem.state = Element.State.Batched
            elem.batch_id = batch_id

        self._db.flush()
        return batch_id

    def send_batch(self, sub, batch_id):
        if sub.custom:
            msg = json.dumps(sub.custom)
        else:
            msg = json.dumps({
                'SubscriptionId': sub.id,
                'BatchId': batch_id,
            })

        sub.endpoint.send_message(ctx=self._ctx, msg=msg)
