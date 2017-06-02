import revolio as rv

from nudge.core.endpoint import Endpoint
from nudge.core.entity import Subscription, Element
import nudge.core.function


class GetActiveBatch(rv.Function):

    def __init__(self, ctx, log, elem_srv, batch_srv):
        super().__init__(ctx)
        self._log = log
        self._elem_srv = elem_srv
        self._batch_srv = batch_srv

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

        batch_id = self(
            sub_id=sub_id,
            force=force,
        )

        # format response

        return {
            'BatchId': batch_id,
        }

    def __call__(self, sub_id, *, force=False):
        self._log.info('Handling call: GetActiveBatch')
        batch_id = self._elem_srv.get_active_batch_id(sub_id)
        if batch_id is not None:
            return batch_id

        if force:
            return self._batch_srv.create_batch()

        return None
