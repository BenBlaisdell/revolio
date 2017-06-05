import enum
import json
import uuid

import revolio as rv
from nudge.core.entity import Element

from nudge.core.orm import BatchOrm


class Batch(rv.Entity):

    @property
    def id(self):
        return self._orm.id

    class State(enum.Enum):
        Unconsumed = 'Unconsumed'
        Consumed = 'Consumed'

    @property
    def state(self):
        return Batch.State[self._orm.state]

    @state.setter
    def state(self, state):
        assert isinstance(state, Batch.State)
        self._orm.state = state.value

    @property
    def sub_id(self):
        return self._orm.sub_id

    @staticmethod
    def create(sub_id):
        return Batch(BatchOrm(
            id=str(uuid.uuid4()),
            state=Batch.State.Unconsumed.value,
            sub_id=sub_id,
            data={},
        ))

    def __str__(self):
        return super().__str__(
            id=self.id,
            sub_id=self.sub_id,
            state=self.state,
        )


class BatchService:

    def __init__(self, ctx, db, elem_srv, sub_srv, log):
        self._ctx = ctx
        self._db = db
        self._elem_srv = elem_srv
        self._sub_srv = sub_srv
        self._log = log

    def get_active_batch(self, sub_id):
        self._log.debug('Getting active batch for subscription {}'.format(sub_id))
        orm = self._db \
            .query(BatchOrm) \
            .filter(BatchOrm.sub_id == sub_id) \
            .filter(BatchOrm.state == Batch.State.Unconsumed.value) \
            .order_by(BatchOrm.created) \
            .first()

        if orm is not None:
            batch = Batch(orm)
            self._log.debug('Found active batch {} for subscription {}'.format(batch.id, sub_id))
            return batch

        self._log.debug('Found no active batch for subscription {}'.format(sub_id))

    def get_batch(self, batch_id):
        self._log.debug('Getting batch {}'.format(batch_id))
        orm = self._db \
            .query(BatchOrm) \
            .filter(BatchOrm.id == batch_id) \
            .filter(BatchOrm.state == Batch.State.Unconsumed.value) \
            .order_by(BatchOrm.created) \
            .first()

        if orm is not None:
            batch = Batch(orm)
            self._log.debug('Found batch {} by id'.format(batch.id))
            return batch

        self._log.debug('Found no batch {} by id'.format(batch_id))

    def get_subscription_batches(self, sub_id, *, prev_id=None, limit=None):
        self._log.debug('Getting batches for subscription {}'.format(sub_id))
        query = self._db \
            .query(BatchOrm) \
            .filter(BatchOrm.sub_id == sub_id) \
            .order_by(BatchOrm.created) \
            .limit(limit)

        # only return batches created after the batch with prev_id
        if prev_id is not None:
            start_point = self._db \
                .query(BatchOrm.created) \
                .get(prev_id) \
                .subquery('start_point')

            query = query.filter(BatchOrm.created > start_point)

        batches = [Batch(orm) for orm in query.all()]
        self._log.debug('Found batches for subscription {s} following batch {b}: {batches}'.format(
            s=sub_id,
            b=prev_id,
            batches=batches,
        ))

        return batches
