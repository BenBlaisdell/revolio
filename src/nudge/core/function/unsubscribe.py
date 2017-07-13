import logging

import revolio as rv
import revolio.serializable
from revolio.function import validate
from revolio.sqlalchemy import autocommit

from nudge.core.entity import Subscription


_log = logging.getLogger(__name__)


class Unsubscribe(rv.function.Function):

    def __init__(self, ctx, db, sub_srv, iris):
        super().__init__(ctx)
        self._db = db
        self._sub_srv = sub_srv
        self._iris = iris

    def format_request(self, sub_id):
        return {
            'SubscriptionId': sub_id,
        }

    @validate(
        subscription_id=rv.serializable.fields.Str(),
    )
    def handle_request(self, request):

        # make call

        self(
            sub_id=request.subscription_id,
        )

        # format response

        return {'Message': 'Success'}

    @autocommit
    def __call__(self, sub_id):
        sub = self._sub_srv.get_subscription(sub_id)
        self._sub_srv.assert_active(sub)

        sub.state = Subscription.State.INACTIVE

        _log.info(f'Removing iris listener {sub.iris_id}')
        self._iris.remove_listener(
            id=sub.iris_id,
        )
