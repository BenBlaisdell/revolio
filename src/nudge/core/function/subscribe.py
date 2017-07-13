import logging
import uuid

import revolio as rv
from revolio.function import validate
from revolio.serializable import KeyFormat
from revolio.sqlalchemy import autocommit

from nudge.core.entity import Subscription


_log = logging.getLogger(__name__)


class Subscribe(rv.function.Function):

    def __init__(self, ctx, db, deferral, iris, config):
        super().__init__(ctx)
        self._db = db
        self._deferral = deferral
        self._iris = iris
        self._config = config

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
        trigger=rv.serializable.fields.Nested(Subscription.Trigger, optional=True),
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
            id=str(uuid.uuid4()),
            state=Subscription.State.ACTIVE,
            bucket=bucket,
            prefix=prefix,
            regex=regex,
            trigger=trigger,
        ))

        self._ensure_listening(sub)

        if backfill:
            sub.state = Subscription.State.BACKFILLING
            self._db.flush()
            self._deferral.send_call(self._ctx.backfill, sub.id)

        return sub

    def _ensure_listening(self, sub):
        _log.info('Adding iris listener')
        env = self._config['Tags']['Environment']
        r = self._iris.add_listener(
            bucket=sub.bucket,
            prefix=sub.prefix,
            protocol='sqs',
            endpoint=self._config['Worker']['S3Events']['QueueArn'],
            tag=f'nudge-{env}-{sub.id}',
        )

        sub.iris_id = r['ListenerId']
        _log.info(f'Created iris listener {sub.iris_id}')
