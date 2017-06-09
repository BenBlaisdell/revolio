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
        self._log.info('Handling request: Unsubscribe')

        # parse parameters

        sub_id = request['SubscriptionId']
        assert isinstance(sub_id, str)

        # make call

        self(sub_id)

        # format response

        return {'Message': 'Success'}

    def __call__(self, sub_id):
        self._log.info('Handling call: Unsubscribe')

        sub = self._sub_srv.get_subscription(sub_id)
        assert sub.state == Subscription.State.ACTIVE

        sub.state = Subscription.State.INACTIVE
        self._db.commit()
