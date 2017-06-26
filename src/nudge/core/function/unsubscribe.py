import revolio as rv

from nudge.core.entity import Subscription
from nudge.core.util import autocommit
from revolio.function import validate


class Unsubscribe(rv.Function):

    def __init__(self, ctx, db, sub_srv):
        super().__init__(ctx)
        self._db = db
        self._sub_srv = sub_srv

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
