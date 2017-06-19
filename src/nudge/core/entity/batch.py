import enum
import logging
import uuid

import revolio as rv
import sqlalchemy as sa

from nudge.core.entity import Entity


_log = logging.getLogger(__name__)


class BatchState(enum.Enum):
    UNCONSUMED = 'UNCONSUMED'
    CONSUMED = 'CONSUMED'


class Batch(Entity):
    __tablename__ = 'batch'

    id = sa.Column(
        sa.String,
        default=lambda: str(uuid.uuid4()),
        primary_key=True,
    )

    State = BatchState
    state = sa.Column(
        sa.Enum(State),
        default=State.UNCONSUMED,
        nullable=False,
    )

    # todo: map to other tables
    sub_id = sa.Column(
        sa.String,
    )

    def __repr__(self):
        return super().__repr__(id=self.id)


# service


class BatchService:

    def __init__(self, ctx, db, elem_srv, sub_srv):
        self._ctx = ctx
        self._db = db
        self._elem_srv = elem_srv
        self._sub_srv = sub_srv

    def get_active_batch(self, sub_id):
        _log.debug('Getting active batch for subscription {}'.format(sub_id))
        batch = self._db \
            .query(Batch) \
            .filter(Batch.sub_id == sub_id) \
            .filter(Batch.state == Batch.State.UNCONSUMED.value) \
            .order_by(Batch.created) \
            .first()

        if batch is not None:
            _log.debug('Found active batch {} for subscription {}'.format(batch.id, sub_id))
            return batch

        _log.debug('Found no active batch for subscription {}'.format(sub_id))

    def get_batch(self, sub_id, batch_id):
        return self._db \
            .query(Batch) \
            .get(batch_id)

    def get_subscription_batches(self, sub_id, *, prev_id=None, limit=None, state=None):
        _log.debug('Getting batches for subscription {}'.format(sub_id))
        query = self._db \
            .query(Batch) \
            .filter(Batch.sub_id == sub_id) \
            .order_by(Batch.created) \
            .limit(limit)

        # only return batches created after the batch with prev_id
        if prev_id is not None:
            start_point = self._db \
                .query(Batch.created) \
                .get(prev_id) \
                .subquery('start_point')

            query = query.filter(Batch.created > start_point)

        if state is not None:
            assert isinstance(state, Batch.State)
            query = query.filter(Batch.state == state.value)

        batches = list(query.all())
        _log.debug('Found batches for subscription {s} following batch {b}: {batches}'.format(
            s=sub_id,
            b=prev_id,
            batches=batches,
        ))

        return batches
