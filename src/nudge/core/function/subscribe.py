import revolio as rv

from nudge.core.entity import Subscription
from nudge.core.util import autocommit


class Subscribe(rv.Function):

    def __init__(self, ctx, db, deferral):
        super().__init__(ctx)
        self._db = db
        self._deferral = deferral

    def format_request(self, bucket, *, prefix=None, regex=None, backfill=False, trigger=None):
        return {
            'Bucket': bucket,
            'Prefix': prefix,
            'Regex': regex,
            'Backfill': backfill,
            'Trigger': trigger,
        }

    def handle_request(self, request):
        bucket = request['Bucket']
        assert isinstance(bucket, str)

        prefix = request.get('Prefix', None)
        assert isinstance(prefix, str) or (prefix is None)

        regex = request.get('Regex', None)
        assert isinstance(regex, str) or (regex is None)

        backfill = request.get('Backfill', False)
        assert isinstance(backfill, bool)

        trigger = request.get('Trigger', None)
        if trigger is not None:
            trigger = Subscription.Trigger.deserialize(trigger)
            assert isinstance(trigger, Subscription.Trigger)

        # make call

        sub = self(
            bucket=bucket,
            prefix=prefix,
            regex=regex,
            trigger=trigger,
            backfill=backfill,
        )

        # format response

        return {
            'SubscriptionId': sub.id,
        }

    @autocommit
    def __call__(self, bucket, *, prefix=None, regex=None, backfill=False, trigger=None):
        sub = self._db.add(Subscription(
            state=Subscription.State.ACTIVE,
            bucket=bucket,
            prefix=prefix,
            regex=regex,
            trigger=trigger,
        ))

        if backfill:
            sub.state = Subscription.State.BACKFILLING
            self._db.flush()
            self._deferral.send_call(self._ctx.backfill, sub.id)

        return sub
