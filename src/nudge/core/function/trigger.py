import revolio as rv

from nudge.core.endpoint import Endpoint


class Trigger(rv.Function):

    def __init__(self, db, sub_srv, log):
        super().__init__()
        self._db = db
        self._sub_srv = sub_srv
        self._log = log

    def format_request(self, sub_id, endpoint, threshold):
        return {
            'SubscriptionId': sub_id,
            'Endpoint': endpoint,
            'Threshold': threshold,
        }

    def handle_request(self, request):
        self._log.info('Handling request: Trigger')

        # parse parameters

        sub_id = request['SubscriptionId']
        assert isinstance(sub_id, str)

        endpoint = Endpoint.deserialize(request['Endpoint'])

        threshold = request.get('Threshold', None)
        assert isinstance(threshold, int) or (threshold is None)

        # make call

        sub = self(
            sub_id=sub_id,
            endpoint=endpoint,
            threshold=threshold,
        )

        # format response

        return {
            'SubscriptionId': sub.id,
        }

    def __call__(self, sub_id, endpoint=None, threshold=0):
        self._log.info('Handling call: Trigger')

        sub = self._sub_srv.get_subscription(sub_id)
        subscription_data = sub.data.copy()
        if endpoint:
            sub['endpoint'] = endpoint
        if threshold:
            sub['threshold'] = threshold
        sub.data = subscription_data

        self._db.commit()
        return sub
