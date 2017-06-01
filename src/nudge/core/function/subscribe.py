import revolio as rv

from nudge.core.endpoint import Endpoint
from nudge.core.entity import Subscription


class Subscribe(rv.Function):

    def __init__(self, db, log):
        super().__init__()
        self._db = db
        self._log = log

    def format_request(self, bucket, endpoint, *, prefix=None, regex=None, threshold=0, custom=None, backfill=False):
        return {
            'Bucket': bucket,
            'Endpoint': endpoint,
            'Prefix': prefix,
            'Regex': regex,
            'Threshold': threshold,
            'Custom': custom,
            'Backfill': backfill,
        }

    def handle_request(self, request):
        self._log.info('Handling request: Subscribe')

        # parse parameters

        bucket = request['Bucket']
        assert isinstance(bucket, str)

        prefix = request.get('Prefix', None)
        assert isinstance(prefix, str) or (prefix is None)

        endpoint = Endpoint.deserialize(request['Endpoint'])

        regex = request.get('Regex', None)
        assert isinstance(regex, str) or (regex is None)

        threshold = request.get('Threshold', None)
        assert isinstance(threshold, int) or (threshold is None)

        custom = request.get('Custom', None)
        assert isinstance(custom, dict) or (custom is None)

        backfill = request.get('Backfill', False)
        assert isinstance(backfill, bool)

        # make call

        sub = self(
            bucket=bucket,
            prefix=prefix,
            endpoint=endpoint,
            regex=regex,
            threshold=threshold,
            custom=custom
        )

        # format response

        return {
            'SubscriptionId': sub.id,
        }

    def __call__(self, bucket, endpoint=None, *, prefix=None, regex=None, threshold=0, custom=None, backfill=False):
        self._log.info('Handling call: Subscribe')

        sub = Subscription.create(
            bucket=bucket,
            endpoint=endpoint,
            prefix=prefix,
            regex=regex,
            threshold=threshold,
            custom=custom,
        )

        self._db.add(sub)
        self._db.flush()

        # send backfill call

        self._db.commit()

        return sub
