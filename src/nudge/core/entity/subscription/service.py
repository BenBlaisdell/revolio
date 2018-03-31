import json
import logging
import uuid

import sqlalchemy as sa

from nudge.core.entity.batch import Batch
from nudge.core.entity.element import Element
from nudge.core.entity.subscription.subscription import Subscription


_log = logging.getLogger(__name__)


class SubscriptionService:

    def __init__(self, ctx, db, elem_srv, ping_srv):
        super(SubscriptionService, self).__init__()
        self._ctx = ctx
        self._db = db
        self._elem_srv = elem_srv
        self._ping_srv = ping_srv

    @staticmethod
    def matches(sub, bucket, key):
        return all([
            bucket == sub.bucket,
            key.startswith(sub.prefix),
            (sub.regex is None) or sub.regex.match(key[len(sub.prefix):]),
        ])

    def get_subscription(self, sub_id):
        return self._db \
            .query(Subscription) \
            .get(sub_id)

    def find_matching_subscriptions(self, bucket, key):
        query = self._db \
            .query(Subscription) \
            .filter(Subscription.state == Subscription.State.ACTIVE.value) \
            .filter(Subscription.bucket == bucket)

        k = sa.sql.expression.bindparam('k', key)
        query = query \
            .filter(k.startswith(Subscription.prefix))

        subs = list(filter(lambda s: self.matches(s, bucket, key), query.all()))

        _log.debug('Found subscriptions matching bucket="{b}" key="{k}": {s}'.format(
            b=bucket,
            k=key,
            s=subs,
        ))

        return subs

    def evaluate(self, sub):
        _log.info(f'Evaluating {sub}')

        if sub.trigger is None:
            _log.info('No trigger attached')
            return

        elems = self._elem_srv.get_batchable_sub_elems(sub.id)
        batch_size = sum(e.size for e in elems)
        num_elems = len(elems)

        if batch_size >= sub.trigger.threshold:
            _log.info(f'{sub} is ready to batch by passing threshold of {sub.trigger.threshold} with {num_elems} elements: {elems}')
            return self._create_and_send_batch(sub, elems)

        _log.info(f'{sub} not ready to batch')
        return None

    def _create_and_send_batch(self, sub, elems):
        batch = self._db.add(Batch(
            id=str(uuid.uuid4()),
            state=Batch.State.UNCONSUMED,
            sub_id=sub.id,
        ))

        for elem in elems:
            assert elem.sub_id == sub.id
            assert elem.state == Element.State.AVAILABLE
            elem.state = Element.State.BATCHED
            elem.batch_id = batch.id

        self._db.flush()

        if sub.trigger.endpoint is not None:
            _log.info('Sending {} trigger message'.format(sub))
            sub.trigger.endpoint.send_message(
                ctx=self._ctx,
                msg=self._ping_srv.get_ping_data(sub),
            )

        return batch

    def assert_active(self, sub):
        if sub.state is not Subscription.State.ACTIVE:
            raise Exception('Subscription state is {}'.format(sub.state.value))
