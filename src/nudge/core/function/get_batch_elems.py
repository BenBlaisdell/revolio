import revolio as rv
import revolio.serializable
from revolio.function import validate
from revolio.sqlalchemy import autocommit


class GetBatchElements(rv.function.Function):

    def __init__(self, ctx, elem_srv, db):
        super().__init__(ctx)
        self._elem_srv = elem_srv
        self._db = db

    def format_request(self, sub_id, batch_id, *, limit=None, offset=0):
        return {
            'SubscriptionId': sub_id,
            'BatchId': batch_id,
            'Limit': limit,
            'Offset': offset,
        }

    @validate(
        subscription_id=rv.serializable.fields.Str(),
        batch_id=rv.serializable.fields.Str(),
        limit=rv.serializable.fields.Int(optional=True, default=None, min=1),
        offset=rv.serializable.fields.Int(optional=True, default=0, min=0),
    )
    def handle_request(self, request):

        # make call
        elems = self(
            sub_id=request.subscription_id,
            batch_id=request.batch_id,
            limit=request.limit,
            offset=request.offset,
        )

        # format response
        return {
            'SubscriptionId': request.subscription_id,
            'BatchId': request.batch_id,
            'Elements': [
                {
                    'Id': elem.id,
                    'Bucket': elem.bucket,
                    'Key': elem.key,
                    'Size': elem.size,
                    'Created': elem.s3_created.strftime('%Y-%m-%d %H:%M:%S'),
                }
                for elem in elems
            ],
        }

    @autocommit
    def __call__(self, sub_id, batch_id, *, limit=None, offset=0):
        return self._elem_srv.get_batch_elems(
            sub_id=sub_id,
            batch_id=batch_id,
            limit=limit,
            offset=offset,
        )
