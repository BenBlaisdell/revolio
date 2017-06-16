import datetime as dt

import revolio as rv
from nudge.core.entity import Element, Batch

from nudge.core.entity.subscription import Subscription
from nudge.core.util import autocommit


class CreateBatch(rv.Function):

    def __init__(self, ctx, sub_srv, elem_srv, db):
        super().__init__(ctx)
        self._sub_srv = sub_srv
        self._elem_srv = elem_srv
        self._db = db

    def format_request(self, sub_id):
        return {
            'SubscriptionId': sub_id,
        }

    def handle_request(self, request):
        sub_id = request['SubscriptionId']
        assert isinstance(sub_id, str)

        # make call

        batch = self(
            sub_id=sub_id,
        )

        # format response

        return {
            'BatchId': batch.id if (batch is not None) else None,
        }

    @autocommit
    def __call__(self, sub_id):
        sub = self._sub_srv.get_subscription(sub_id)
        self._sub_srv.assert_active(sub)

        elems = self._elem_srv.get_sub_elems(sub_id, state=Element.State.AVAILABLE)
        if len(elems) == 0:
            return None

        batch = self._db.add(Batch.create(sub_id))

        for elem in elems:
            assert elem.sub_id == sub_id
            assert elem.state == Element.State.AVAILABLE
            elem.state = Element.State.BATCHED
            elem.batch_id = batch.id

        return batch
