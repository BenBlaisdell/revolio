import revolio as rv
import revolio.function
import revolio.serializable
from revolio.function import validate
from revolio.sqlalchemy import autocommit

from nudge.core.entity import Element


class HandleObjectCreated(rv.function.Function):

    def __init__(self, ctx, db, sub_srv, batch_srv, elem_srv):
        super().__init__(ctx)
        self._db = db
        self._sub_srv = sub_srv
        self._batch_srv = batch_srv
        self._elem_srv = elem_srv

    def format_request(self, bucket, key, size, created):
        return {
            'Bucket': bucket,
            'Key': key,
            'Size': size,
            'Created': created,
        }

    @validate(
        bucket=rv.serializable.fields.Str(),
        key=rv.serializable.fields.Str(),
        size=rv.serializable.fields.Int(),
        created=rv.serializable.fields.DateTime(),
    )
    def handle_request(self, request):

        # make call

        results = self(
            bucket=request.bucket,
            key=request.key,
            size=request.size,
            created=request.created,
        )

        # format response

        return {
            'MatchingSubscriptions': {
                elem.sub_id: {
                    'ElementId': elem.id,
                    'BatchId': None if (batch is None) else batch.id,
                }
                for elem, batch in results
            },
        }

    @autocommit
    def __call__(self, bucket, key, size, created):
        return [
            self._handle_matching_sub(sub, bucket=bucket, key=key, size=size, created=created)
            for sub in self._sub_srv.find_matching_subscriptions(bucket, key)
        ]

    def _handle_matching_sub(self, sub, bucket, key, size, created):
        elem = self._db.add(Element(
            sub_id=sub.id,
            bucket=bucket,
            key=key,
            size=size,
            s3_created=created,
        ))

        batch = self._sub_srv.evaluate(sub)
        return elem, batch
