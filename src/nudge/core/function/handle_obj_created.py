import datetime as dt
import json

import revolio as rv

from nudge.core.entity import Element, Batch


class HandleObjectCreated(rv.Function):

    def __init__(self, ctx, db, sub_srv, batch_srv, elem_srv, log):
        super().__init__(ctx)
        self._db = db
        self._sub_srv = sub_srv
        self._batch_srv = batch_srv
        self._elem_srv = elem_srv
        self._log = log

    def format_request(self, bucket, key, size, created):
        return {
            'Bucket': bucket,
            'Key': key,
            'Size': size,
            'Created': created,
        }

    def handle_request(self, request):
        bucket = request['Bucket']
        assert isinstance(bucket, str)

        key = request['Key']
        assert isinstance(key, str)

        size = request['Size']
        assert isinstance(size, int)

        created = request['Created']
        assert isinstance(created, str)
        created = dt.datetime.strptime(created, '%Y-%m-%d %H:%M:%S')

        # format response

        return {
            'MatchingSubscriptions': {
                elem.sub_id: {
                    'ElementId': elem.id,
                    'BatchId': None if (batch is None) else batch.id,
                }
                for elem, batch in self(
                    bucket=bucket,
                    key=key,
                    size=size,
                    created=created,
                )
            },
        }

    def __call__(self, bucket, key, size, created):
        result = [
            self._handle_matching_sub(sub, bucket=bucket, key=key, size=size, created=created)
            for sub in self._sub_srv.find_matching_subscriptions(bucket, key)
        ]

        self._db.commit()
        return result

    def _handle_matching_sub(self, sub, bucket, key, size, created):
        elem = self._db.add(Element.create(
            sub_id=sub.id,
            bucket=bucket,
            key=key,
            size=size,
            created=created,
        ))

        batch = self._sub_srv.evaluate(sub)
        return elem, batch
