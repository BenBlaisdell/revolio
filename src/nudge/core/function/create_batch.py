import uuid

import revolio as rv
import revolio.serializable
from revolio.function import validate
from revolio.sqlalchemy import autocommit

from nudge.core.entity import Element, Batch



class CreateBatch(rv.function.Function):

    def __init__(self, ctx, sub_srv, elem_srv, db):
        super().__init__(ctx)
        self._sub_srv = sub_srv
        self._elem_srv = elem_srv
        self._db = db

    def format_request(self, sub_id):
        return {
            'SubscriptionId': sub_id,
        }

    @validate(
        subscription_id=rv.serializable.fields.Str(),
    )
    def handle_request(self, request):

        # make call

        batch = self(
            sub_id=request.subscription_id,
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

        batch = self._db.add(Batch(
            id=str(uuid.uuid4()),
            state=Batch.State.UNCONSUMED,
            sub_id=sub_id,
        ))

        for elem in elems:
            assert elem.sub_id == sub_id
            assert elem.state == Element.State.AVAILABLE
            elem.state = Element.State.BATCHED
            elem.batch_id = batch.id

        return batch
