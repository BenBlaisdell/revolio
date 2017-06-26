import revolio as rv

from nudge.core.util import autocommit
from revolio.function import validate


class GetBatchElements(rv.Function):

    def __init__(self, ctx, elem_srv, db):
        super().__init__(ctx)
        self._elem_srv = elem_srv
        self._db = db

    def format_request(self, sub_id, batch_id, *, offset=0, limit=None):
        return {
            'SubscriptionId': sub_id,
            'BatchId': batch_id,
            'Offset': offset,
            'Limit': limit,
        }

    @validate(
        subscription_id = rv.serializable.fields.Str(),
        batch_id = rv.serializable.fields.Str(),
        offset = rv.serializable.fields.Int(optional=True, default=0, min=0),
        limit = rv.serializable.fields.Int(optional=True, default=None, min=1),
    )
    def handle_request(self, request):

        # make call
        elems = self(
            sub_id=request.subscription_id,
            batch_id=request.batch_id,
            offset=request.offset,
            limit=request.limit,
        )

        # format response
        return {
            'SubscriptionId': request.sub_id,
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
    def __call__(self, sub_id, batch_id, *, offset=0, limit=None):
        return self._elem_srv.get_batch_elems(
            sub_id=sub_id,
            batch_id=batch_id,
            offset=offset,
            limit=limit,
        )