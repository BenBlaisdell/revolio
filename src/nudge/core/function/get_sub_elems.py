import revolio as rv
import revolio.serializable
from revolio.function import validate
from revolio.sqlalchemy import autocommit


class GetSubscriptionElements(rv.function.Function):
    """Get elements belonging to a subscription.

    params:
        SubscriptionId (str)
        Limit (int)
        Offset (int)
    returns:
        SubscriptionId (str)
        Elements (list[Element])
    """

    def __init__(self, ctx, elem_srv, db):
        super().__init__(ctx)
        self._elem_srv = elem_srv
        self._db = db

    def format_request(self, sub_id, *, limit=None, offset=0):
        return {
            'SubscriptionId': sub_id,
            'Limit': limit,
            'Offset': offset,
        }

    @validate(
        subscription_id=rv.serializable.fields.Str(),
        limit=rv.serializable.fields.Int(optional=True, default=None, min=1),
        offset=rv.serializable.fields.Int(optional=True, default=0, min=0),
    )
    def handle_request(self, request):

        # make call
        elems = self(
            sub_id=request.subscription_id,
            limit=request.limit,
            offset=request.offset,
        )

        # format response
        return {
            'SubscriptionId': request.subscription_id,
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
    def __call__(self, sub_id, *, offset=0, limit=None):
        return self._elem_srv.get_sub_elems(
            sub_id=sub_id,
            limit=limit,
            offset=offset,
        )
