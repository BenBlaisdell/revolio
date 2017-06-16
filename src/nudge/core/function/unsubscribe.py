import revolio as rv

from nudge.core.entity import Subscription
from nudge.core.util import autocommit


class Unsubscribe(rv.Function):

    def __init__(self, ctx, db, sub_srv):
        super().__init__(ctx)
        self._db = db
        self._sub_srv = sub_srv

    def format_request(self, sub_id):
        return {
            'SubscriptionId': sub_id,
        }

    def handle_request(self, request):
        sub_id = request['SubscriptionId']
        assert isinstance(sub_id, str)

        # make call

        self(sub_id)

        # format response

        return {'Message': 'Success'}

    @autocommit
    def __call__(self, sub_id):
        sub = self._sub_srv.get_subscription(sub_id)
        self._sub_srv.assert_active(sub)

        sub.state = Subscription.State.INACTIVE
