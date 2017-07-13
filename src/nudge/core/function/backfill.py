import logging

import revolio as rv
import revolio.serializable
from revolio.function import validate
from revolio.sqlalchemy import autocommit

from nudge.core.entity import Subscription, Element


_log = logging.getLogger(__name__)


class Backfill(rv.function.Function):

    def __init__(self, ctx, db, sub_srv, s3, deferral):
        super().__init__(ctx)
        self._db = db
        self._sub_srv = sub_srv
        self._s3 = s3
        self._deferral = deferral

    def format_request(self, sub_id, *, token=None):
        return {
            'SubscriptionId': sub_id,
            'ContinuationToken': token,
        }

    @validate(
        subscription_id=rv.serializable.fields.Str(),
        continuation_token=rv.serializable.fields.Str(optional=True),
    )
    def handle_request(self, request):

        # make call

        elems, backfill_complete = self(
            sub_id=request.subscription_id,
            token=request.continuation_token,
        )

        # format response

        return {
            'ElementIds': [e.id for e in elems],
            'BackfillComplete': backfill_complete,
        }

    @autocommit
    def __call__(self, sub_id, *, token=None):
        sub = self._sub_srv.get_subscription(sub_id)

        if sub.state is not Subscription.State.BACKFILLING:
            raise Exception(f'Subscription is in state {sub.state.value}')

        r = self._s3.list_objects_v2(
            Bucket=sub.bucket,
            Prefix=sub.prefix,
            MaxKeys=1000,  # max allowed by api
            **(dict(ContinuationToken=token) if (token is not None) else {})
        )

        backfill_complete = not r.get('IsTruncated', False)
        if not backfill_complete:
            next_token = r['ContinuationToken']
            _log.info(f'Sending deferred {sub} backfill continuation call with token {next_token}')
            self._deferral.send_call(self, sub.id, token=token)

        elems = [
            self._db.add(Element(
                sub_id=sub.id,
                state=Element.State.AVAILABLE,
                bucket=sub.bucket,
                key=obj_data['Key'],
                size=obj_data['Size'],
                s3_created=obj_data['LastModified'],
            ))
            for obj_data in r.get('Contents', [])
            if self._sub_srv.matches(
                sub=sub,
                bucket=sub.bucket,
                key=obj_data['Key'],
            )
        ]

        if backfill_complete:
            _log.info('{} backfilling is complete'.format(sub))
            sub.state = Subscription.State.ACTIVE
            self._sub_srv.evaluate(sub)

        return elems, backfill_complete
