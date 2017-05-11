from nudge.entity.element import Element
from nudge.entity.subscription import Subscription


class FunctionDirectory:

    def __init__(self, ctx):
        self._ctx = ctx

    def subscribe(self, bucket, endpoint, *, prefix=None, regex=None, threshold=0):
        sub = Subscription.create(
            bucket=bucket,
            endpoint=endpoint,
            prefix=prefix,
            regex=regex,
            threshold=threshold,
        )

        self._ctx.session.add(sub.to_orm())
        self._ctx.session.commit()

        return sub

    def handle_obj_created(self, bucket, key, size, time):
        return [
            self._handle_matching_sub(sub, bucket, key, size, time)
            for sub in self._ctx.sub_srv.find_matching_subscriptions(bucket, key)
        ]

    def handle_matching_sub(self, sub_id, bucket, key, size, time):
        return self._handle_matching_sub(
            sub=self._ctx.sub_srv.get_sub(sub_id),
            bucket=bucket,
            key=key,
            size=size,
            time=time,
        )

    def evaluate_sub(self, sub_id):
        return self._evaluate_sub(self._ctx.sub_srv.get_sub(sub_id))

    def consume(self, elem_ids):
        pass

    def unsubscribe(self, sub_id):
        pass

    def _handle_matching_sub(self, sub, bucket, key, size, time):
        elem = Element.create(
            sub_id=sub.id,
            bucket=bucket,
            key=key,
            size=size,
            time=time,
        )

        self._ctx.session.add(elem.to_orm())
        triggered = self._evaluate_sub(sub)

        return elem, triggered

    def _evaluate_sub(self, sub):
        elems = self._ctx.elem_srv.get_sub_elems(sub.id)
        if _batch_size(elems) >= sub.threshold:
            self._ctx.batch_srv.send_batch(sub, elems)
            return True

        return False


def _batch_size(elems):
    return sum(map(lambda e: e.size, elems))
