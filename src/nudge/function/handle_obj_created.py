from nudge.entity.element import Element


class HandleObjectCreated:

    def __init__(self, session, sub_srv, batch_srv, elem_srv):
        self._session = session
        self._sub_srv = sub_srv
        self._batch_srv = batch_srv
        self._elem_srv = elem_srv

    def __call__(self, bucket, key, size, time):
        return [
            self._handle_matching_sub(sub, bucket, key, size, time)
            for sub in self._sub_srv.find_matching_subscriptions(bucket, key)
        ]

    def _handle_matching_sub(self, sub, bucket, key, size, time):
        elem = Element.create(
            sub_id=sub.id,
            bucket=bucket,
            key=key,
            size=size,
            time=time,
        )

        self._session.add(elem.to_orm())
        triggered = self._evaluate_sub(sub)

        return elem, triggered

    def _evaluate_sub(self, sub):
        elems = self._elem_srv.get_sub_elems(sub.id)
        if _batch_size(elems) >= sub.threshold:
            self._batch_srv.send_batch(sub, elems)
            return True

        return False


def _batch_size(elems):
    return sum(map(lambda e: e.size, elems))
