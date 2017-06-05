import revolio as rv

from nudge.core.endpoint import Endpoint
from nudge.core.entity import Subscription, Element, Batch
import nudge.core.function


class GetActiveBatch(rv.Function):

    def __init__(self, ctx, log, elem_srv, batch_srv, sub_srv, db):
        super().__init__(ctx)
        self._log = log
        self._elem_srv = elem_srv
        self._batch_srv = batch_srv
        self._sub_srv = sub_srv
        self._db = db

    def format_request(self, sub_id, *, force=False):
        return {
            'SubscriptionId': sub_id,
            'Force': force,
        }

    def handle_request(self, request):
        self._log.info('Handling request: GetActiveBatch')

        # parse parameters

        sub_id = request['SubscriptionId']
        assert isinstance(sub_id, str)

        force = request.get('Force', False)
        assert isinstance(force, bool)

        # make call

        batch = self(
            sub_id=sub_id,
            force=force,
        )

        # format response

        return {
            'BatchId': batch.id if (batch is not None) else None,
        }

    def __call__(self, sub_id, *, force=False):
        self._log.info('Handling call: GetActiveBatch')

        batch = self._batch_srv.get_active_batch(sub_id)

        if (batch is None) and force:
            batch = self._create_batch(sub_id)

        self._db.commit()
        return batch

    def _create_batch(self, sub_id):
        batch = self._db.add(Batch.create(sub_id))

        for elem in self._elem_srv.get_sub_elems(sub_id, state=Element.State.Unconsumed):
            assert elem.sub_id == sub_id
            assert elem.state == Element.State.Unconsumed
            elem.state = Element.State.Batched
            elem.batch_id = batch.id

        self._db.flush()
        return batch
