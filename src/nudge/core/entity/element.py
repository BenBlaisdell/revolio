import datetime as dt
import enum
import uuid

import revolio as rv
import sqlalchemy as sa

from nudge.core.entity import Orm


class Element(rv.Entity):

    @property
    def id(self):
        return self._orm.id

    class State(enum.Enum):
        AVAILABLE = 'AVAILABLE'
        BATCHED = 'BATCHED'

    @property
    def state(self):
        return Element.State[self._orm.state]

    @state.setter
    def state(self, state):
        assert isinstance(state, Element.State)
        self._orm.state = state.value

    @property
    def batch_id(self):
        return self._orm.batch_id

    @batch_id.setter
    def batch_id(self, batch_id):
        self._orm.batch_id = batch_id

    @property
    def sub_id(self):
        return self._orm.sub_id

    @property
    def bucket(self):
        return self._orm.data['bucket']

    @property
    def key(self):
        return self._orm.data['key']

    @property
    def size(self):
        return int(self._orm.data['size'])

    @property
    def s3_created(self):
        return dt.datetime.strptime(self._orm.data['created'], '%Y-%m-%d %H:%M:%S')

    @staticmethod
    def create(sub_id, bucket, key, size, created, *, batch_id=None):
        return Element(ElementOrm(
            id=str(uuid.uuid4()),
            state=Element.State.AVAILABLE.value,
            sub_id=sub_id,
            batch_id=batch_id,
            data=dict(
                bucket=bucket,
                key=key,
                size=size,
                created=dt.datetime.strftime(created, '%Y-%m-%d %H:%M:%S'),
            )
        ))

    def __str__(self):
        return super().__str__(
            id=self.id,
            sub_id=self.sub_id,
            state=self.state,
        )


# orm


class ElementOrm(Orm):
    __tablename__ = 'element'

    id = sa.Column(sa.String, primary_key=True)
    state = sa.Column(sa.String)
    sub_id = sa.Column(sa.String)
    batch_id = sa.Column(sa.String)


# service


class ElementService:

    def __init__(self, db, log):
        self._db = db
        self._log = log

    def get_elements(self, elem_ids):
        elems = [
            Element(orm)
            for orm in self._db
                .query(ElementOrm)
                .filter(ElementOrm.id.in_(elem_ids))
                .all()
        ]

        assert len(elems) == len(elem_ids)
        self._log.debug('Found elements by id: {}'.format(elems))
        return elems

    def get_sub_elems(self, sub_id, *, state=Element.State.AVAILABLE):
        elems = [
            Element(orm)
            for orm in self._db
                .query(ElementOrm)
                .filter(ElementOrm.sub_id == sub_id)
                .filter(ElementOrm.state == state.value)
                .all()
        ]

        self._log.debug('Found elements for subscription {}: {}'.format(sub_id, elems))
        return elems

    def get_batch_elems(self, batch, *, offset=0, limit=None):
        elems = [
            Element(orm)
            for orm in self._db
                .query(ElementOrm)
                .filter(ElementOrm.sub_id == batch.sub_id)
                .filter(ElementOrm.state == Element.State.BATCHED.value)
                .filter(ElementOrm.batch_id == batch.id)
                .limit(limit)
                .offset(offset)
                .all()
        ]

        self._log.debug('Found elements for {}: {}'.format(batch, elems))
        return elems
