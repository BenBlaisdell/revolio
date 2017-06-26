import revolio as rv

from nudge.core.entity import Subscription
from nudge.core.entity.subscription.trigger import SubscriptionTrigger
from nudge.core.util import autocommit
from revolio.function import validate
from revolio.serializable import KeyFormat


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
            'Trigger': trigger.serialize(key_format=KeyFormat.Camel) if (trigger is not None) else None,
        }

    @validate(
        bucket=rv.serializable.fields.Str(),
        prefix=rv.serializable.fields.Str(optional=True),
        regex=rv.serializable.fields.Str(optional=True,),
        backfill=rv.serializable.fields.Bool(optional=True, default=False),
        trigger=rv.serializable.fields.Nested(SubscriptionTrigger),
    )
    def handle_request(self, request):

        # make call

        sub = self(
            bucket=request.bucket,
            prefix=request.prefix,
            regex=request.regex,
            backfill=request.backfill,
            trigger=request.trigger,
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
