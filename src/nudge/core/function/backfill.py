import revolio as rv

from nudge.core.entity import Subscription, Element


class Backfill(rv.Function):

    def __init__(self, ctx, db, log, sub_srv, s3, deferral):
        super().__init__(ctx)
        self._db = db
        self._log = log
        self._sub_srv = sub_srv
        self._s3 = s3
        self._deferral = deferral

    def format_request(self, sub_id, *, token=None):
        return {
            'SubscriptionId': sub_id,
            'ContinuationToken': token,
        }

    def handle_request(self, request):
        self._log.info('Handling request: Backfill')

        # parse parameters

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

    def __call__(self, sub_id, *, token=None):
        self._log.info('Handling call: Backfill')

        sub = self._sub_srv.get_subscription(sub_id)
        assert sub.state == Subscription.State.Backfilling

        r = self._s3.list_objects_v2(
            Bucket=sub.bucket,
            MaxKeys=1000,  # max allowed by api
            **(dict(ContinuationToken=token) if (token is not None) else {})
        )

        backfill_complete = not r.get('IsTruncated', False)

        if not backfill_complete:
            self._deferral.send_call(
                self,
                sub.id,
                token=r['ContinuationToken'],
            )

        elems = [
            self._db.add(Element.create(
                sub_id=sub.id,
                bucket=sub.bucket,
                key=obj_data['Key'],
                size=obj_data['Size'],
                created=obj_data['LastModified'],
            ))
            for obj_data in r['Contents']
        ]

        if backfill_complete:
            sub.state = Subscription.State.Active

        self._db.commit()

        return elems, backfill_complete
