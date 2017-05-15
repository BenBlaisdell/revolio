import re

from nudge.endpoint import Endpoint
from nudge.entity.subscription import Subscription


class Subscribe:

    def __init__(self, db, log):
        self._db = db
        self._log = log

    def handle_request(self, request):
        self._log.info('Handling request: Subscribe')

        # parse parameters

        bucket = request['Bucket']
        assert isinstance(bucket, str)

        prefix = request.get('Prefix', None)
        assert isinstance(prefix, str) or (prefix is None)

        e_protocol = request['Endpoint']['Protocol']
        e_params = request['Endpoint']['Parameters']
        endpoint = Endpoint.deserialize(request['Endpoint'])

        regex = request.get('Regex', None)
        assert isinstance(regex, str) or (regex is None)

        threshold = request.get('Threshold', None)
        assert isinstance(threshold, int) or (threshold is None)

        # make call

        sub = self(
            bucket=bucket,
            prefix=prefix,
            endpoint=endpoint,
            regex=regex,
            threshold=threshold,
        )

        # format response

        return {
            'SubscriptionId': sub.id,
        }

    def __call__(self, bucket, endpoint, *, prefix=None, regex=None, threshold=0):
        self._log.info('Handling call: Subscribe')

        sub = Subscription.create(
            bucket=bucket,
            endpoint=endpoint,
            prefix=prefix,
            regex=regex,
            threshold=threshold,
        )

        self._db.add(sub)
        self._db.commit()

        return sub
