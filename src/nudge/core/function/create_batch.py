import datetime as dt

import revolio as rv
from nudge.core.entity import Element, Batch

from nudge.core.entity.subscription import Subscription


class CreateBatch(rv.Function):

    def __init__(self, ctx, elem_srv, log, db):
        super().__init__(ctx)
        self._elem_srv = elem_srv
        self._log = log
        self._db = db

    def format_request(self, sub_id):
        return {
            'SubscriptionId': sub_id,
        }

    def handle_request(self, request):
        self._log.info('Handling request: CreateBatch')

        sub_id = request['SubscriptionId']
        assert isinstance(sub_id, str)

        # make call

        batch_id = self(
            sub_id=sub_id,
        )

        # format response

        return {
            'BatchId': batch_id,
        }

    def __call__(self, sub_id):
        self._log.info('Handling call: CreateBatch')

        elems = self._elem_srv.get_sub_elems(sub_id, state=Element.State.Unconsumed)
        if len(elems) == 0:
            return None

        batch = self._db.add(Batch.create(sub_id))

        for elem in elems:
            assert elem.sub_id == sub_id
            assert elem.state == Element.State.Unconsumed
            elem.state = Element.State.Batched
            elem.batch_id = batch.id

        self._db.commit()

        return elems
