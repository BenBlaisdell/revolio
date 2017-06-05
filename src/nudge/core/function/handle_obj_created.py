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
        self._log.info('Handling request: HandleObjectCreated')

        # parse parameters

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
                    'Triggered': (batch is not None),
                    'BatchId': batch,
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
        self._log.info('Handling call: HandleObjectCreated')

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

        return elem, self._evaluate_sub(sub)

    def _evaluate_sub(self, sub):
        elems = self._elem_srv.get_sub_elems(sub.id, state=Element.State.Unconsumed)
        if _batch_size(elems) >= sub.trigger.threshold:
            return self._create_and_send_batch(sub, elems)

        return None

    def _create_and_send_batch(self, sub, elems):
        batch = self._db.add(Batch.create(sub.id))

        for elem in elems:
            assert elem.sub_id == sub.id
            assert elem.state == Element.State.Unconsumed
            elem.state = Element.State.Batched
            elem.batch_id = batch.id

        self._db.flush()

        if sub.trigger.custom is not None:
            msg = json.dumps(sub.trigger.custom)
        else:
            msg = json.dumps({
                'SubscriptionId': sub.id,
                'BatchId': batch.id,
            })

        sub.trigger.endpoint.send_message(ctx=self._ctx, msg=msg)

        return batch


def _batch_size(elems):
    return sum(e.size for e in elems)
