from nudge.entity.element import Element
from nudge.entity.subscription import Subscription


class FunctionDirectory:

    def __init__(self, ctx):
        self._ctx = ctx

    def subscribe(self, bucket, endpoint, *, prefix=None, regex=None, threshold=0):
        return Subscription.create(
            bucket=bucket,
            endpoint=endpoint,
            prefix=prefix,
            regex=regex,
            threshold=threshold,
        )

    def handle_obj_created(self, bucket, key, size, time):
        return [
            (
                Element.create(
                    sub_id=sub_id,
                    bucket=bucket,
                    key=key,
                    size=size,
                    time=time,
                ),
                triggered,
            )
            for sub_id, triggered in [
                ('dummy-elem-id-1', True),
                ('dummy-elem-id-2', True),
                ('dummy-elem-id-3', False),
            ]
        ]

    def consume(self, elem_ids):
        pass

    def unsubscribe(self, sub_id):
        pass
