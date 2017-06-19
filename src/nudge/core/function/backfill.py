import logging

import revolio as rv

from nudge.core.entity import Subscription, Element
from nudge.core.util import autocommit


_log = logging.getLogger(__name__)


class Backfill(rv.Function):

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

    def handle_request(self, request):
        sub_id = request['SubscriptionId']
        assert isinstance(sub_id, str)

        token = request.get('ContinuationToken', None)
        assert isinstance(token, str) or (token is None)

        # make call

        elems, backfill_complete = self(
            sub_id=sub_id,
            token=token,
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
            raise Exception('Subscription is in state'.format(sub.state.value))

        r = self._s3.list_objects_v2(
            Bucket=sub.bucket,
            Prefix=sub.prefix,
            MaxKeys=1000,  # max allowed by api
            **(dict(ContinuationToken=token) if (token is not None) else {})
        )

        backfill_complete = not r.get('IsTruncated', False)
        if not backfill_complete:
            _log.info('Sending deferred {s} backfill continuation call with token {t}'.format(
                s=sub, t=r['ContinuationToken'],
            ))
            self._deferral.send_call(
                self,
                sub.id,
                token=r['ContinuationToken'],
            )

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
