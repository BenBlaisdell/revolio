import datetime as dt

import revolio as rv

from nudge.core.entity.subscription import Subscription


class GetBatchElements(rv.Function):

    def __init__(self, ctx, elem_srv, log, db):
        super().__init__(ctx)
        self._elem_srv = elem_srv
        self._log = log
        self._db = db

    def format_request(self, sub_id, batch_id, *, offset=0, limit=None):
        return {
            'SubscriptionId': sub_id,
            'BatchId': batch_id,
            'Offset': offset,
            'Limit': limit,
        }

    def handle_request(self, request):
        self._log.info('Handling request: GetBatchElements')

        subscription_id = request['SubscriptionId']
        assert isinstance(subscription_id, str)

        batch_id = request['BatchId']
        assert isinstance(batch_id, str)

        offset = request.get('Offset', 0)
        assert isinstance(offset, int)

        limit = request.get('Limit', None)
        assert isinstance(limit, int) or (limit is None)

        # make call
        elems = self(
            subscription_id=subscription_id,
            batch_id=batch_id,
            offset=offset,
            limit=limit,
        )

        # format response
        return {
            'SubscriptionId': subscription_id,
            'BatchId': batch_id,
            'Elements': [
                {
                    'Id': elem.id,
                    'Bucket': elem.bucket,
                    'Key': elem.key,
                    'Size': elem.size,
                    'Created': dt.datetime.strftime(elem.s3_created, '%Y-%m-%d %H:%M:%S'),
                }
                for elem in elems
            ],
        }

    def __call__(self, sub_id, batch_id, *, offset=0, limit=None):
        self._log.info('Handling call: GetBatchElements')
        elems = self._elem_srv.get_batch_elems(
            sub_id=sub_id,
            batch_id=batch_id,
            offset=offset,
            limit=limit,
        )

        self._db.commit()
        return elems
