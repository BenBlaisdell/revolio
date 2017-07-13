import revolio as rv
import revolio.serializable
from revolio.function import validate
from revolio.sqlalchemy import autocommit

from nudge.core.entity import Batch


class Consume(rv.function.Function):

    def __init__(self, ctx, db, batch_srv, elem_srv):
        super().__init__(ctx)
        self._db = db
        self._batch_srv = batch_srv
        self._elem_srv = elem_srv

    def format_request(self, sub_id, batch_id):
        return {
            'SubscriptionId': sub_id,
            'BatchId': batch_id,
        }

    @validate(
        subscription_id=rv.serializable.fields.Str(),
        batch_id=rv.serializable.fields.Str(),
    )
    def handle_request(self, request):

        # make call

        self(
            sub_id=request.subscription_id,
            batch_id=request.batch_id,
        )

        # format response

        return {'Message': 'Success'}

    @autocommit
    def __call__(self, sub_id, batch_id):
        batch = self._batch_srv.get_batch(
            sub_id=sub_id,
            batch_id=batch_id,
        )

        if batch.state is not Batch.State.UNCONSUMED:
            raise Exception(f'Batch state is {batch.state.value}')

        batch.state = Batch.State.CONSUMED
