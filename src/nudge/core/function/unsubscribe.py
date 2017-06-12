import revolio as rv

from nudge.core.entity import Subscription


class Unsubscribe(rv.Function):

    def __init__(self, ctx, db, sub_srv, log):
        super().__init__(ctx)
        self._db = db
        self._sub_srv = sub_srv
        self._log = log

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

    def __call__(self, sub_id):
        sub = self._sub_srv.get_subscription(sub_id)
        self._sub_srv.assert_active(sub)

        sub.state = Subscription.State.INACTIVE
        self._db.commit()
