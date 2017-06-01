import datetime as dt

import revolio as rv

from nudge.core.entity.subscription import Subscription


class GetBatch(rv.Function):

    def __init__(self, elem_srv, log):
        super().__init__()
        self._elem_srv = elem_srv
        self._log = log

    def format_request(self, sub_id, *, offset=0, limit=None, state=None, gte_s3_path=None):
        return {
            'SubscriptionId': sub_id,
            'Offset': offset,
            'Limit': limit,
            'State': state.value if (state is not None) else None,
            'GteS3Path': gte_s3_path,
        }

    def handle_request(self, request):
        self._log.info('Handling request: GetBatch')

        subscription_id = request['SubscriptionId']
        assert isinstance(subscription_id, str)

        offset = request.get('Offset', 0)
        assert isinstance(offset, int)

        limit = request.get('Limit', None)
        assert isinstance(limit, int) or (limit is None)

        state = request.get('State', None)
        state = Subscription.State[state] if (state is not None) else None

        gte_s3_path = request.get('GteS3Path', None)
        assert isinstance(gte_s3_path, str) or (gte_s3_path is None)

        # make call
        elems = self(subscription_id=subscription_id, offset=offset, limit=limit, state=state, gte_s3_path=gte_s3_path)

        # format response
        return {
            'SubscriptionId': subscription_id,
            'Elements': [
                {
                    'Id': elem.id,
                    'Bucket': elem.bucket,
                    'Key': elem.key,
                    'Size': elem.size,
                    'S3Created': dt.datetime.strftime(elem.s3_created, '%Y-%m-%d %H:%M:%S'),
                    'Updated': dt.datetime.strftime(elem.updated, '%Y-%m-%d %H:%M:%S'),
                }
                for elem in elems
            ],
        }

    def __call__(self, sub_id, *, offset=0, limit=None, state=None, gte_s3_path=None):
        self._log.info('Handling call: GetBatch')
        return self._elem_srv.get_sub_elems_by_id(
            sub_id=sub_id,
            offset=offset,
            limit=limit,
            state=state,
            gte_s3_path=gte_s3_path
        )
