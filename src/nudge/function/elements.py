import datetime as dt


class Elements:
    def __init__(self, elem_srv, log):
        self._elem_srv = elem_srv
        self._log = log

    def handle_request(self, request):
        self._log.info('Handling request: Subscribe')

        subscription_id = request['SubscriptionId']
        assert isinstance(subscription_id, str)

        offset = request.get('Offset')
        if offset:
            assert isinstance(subscription_id, int)

        limit = request.get('Limit')
        if limit:
            assert isinstance(subscription_id, int)

        state = request.get('State')
        if state:
            assert isinstance(subscription_id, str)

        gte_s3_path = request['GteS3Path']
        if gte_s3_path:
            assert isinstance(subscription_id, str)

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

    def __call__(self, subscription_id, offset, limit, state, gte_s3_path):
        self._log.info('Handling call: Elements')
        return self._elem_srv.get_sub_elems_by_id(
            sub_id=subscription_id,
            offset=offset,
            limit=limit,
            state=state,
            gte_s3_path=gte_s3_path
        )
