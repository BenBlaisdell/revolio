import revolio as rv

from nudge.core.endpoint import Endpoint
from nudge.core.entity import Subscription, Element
import nudge.core.function


class CreateBatch(rv.Function):

    def __init__(self, ctx, db, log, sub_srv, elem_srv, batch_srv):
        super().__init__(ctx)
        self._db = db
        self._log = log
        self._sub_srv = sub_srv
        self._elem_srv = elem_srv
        self._batch_srv = batch_srv

    def format_request(self, sub_id):
        return {
            'SubscriptionId': sub_id,
        }

    def handle_request(self, request):
        self._log.info('Handling request: CreateBatch')

        # parse parameters

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

        sub = self._sub_srv.get_subscription(sub_id)
        elems = self._elem_srv.get_sub_elems(sub, state=Element.State.Unconsumed)
        self._batch_srv.create_batch(sub, elems)

        return sub
