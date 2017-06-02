import datetime as dt
import enum
import uuid

import revolio as rv

from nudge.core.orm import ElementOrm


class Element(rv.Entity):

    @property
    def id(self):
        return self._orm.id

    class State(enum.Enum):
        Unconsumed = 'Unconsumed'
        Batched = 'Batched'
        Consumed = 'Consumed'

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

    @property
    def updated(self):
        return dt.datetime.strptime(self._orm.updated, '%Y-%m-%d %H:%M:%S')

    @staticmethod
    def create(sub_id, bucket, key, size, created, *, batch_id=None):
        return Element(ElementOrm(
            id=str(uuid.uuid4()),
            state=Element.State.Unconsumed.value,
            sub_id=sub_id,
            batch_id=batch_id,
            data=dict(
                bucket=bucket,
                key=key,
                size=size,
                created=dt.datetime.strftime(created, '%Y-%m-%d %H:%M:%S'),
            )
        ))


class ElementService:

    def __init__(self, db):
        self._db = db

    def get_elements(self, elem_ids):
        elems = [
            Element(orm)
            for orm in self._db
                .query(ElementOrm)
                .filter(ElementOrm.id.in_(elem_ids))
                .all()
        ]

        assert len(elems) == len(elem_ids)
        return elems

    def get_sub_elems(self, sub, *, state=Element.State.Unconsumed):
        return [
            Element(orm)
            for orm in self._db
                .query(ElementOrm)
                .filter(ElementOrm.sub_id == sub.id)
                .filter(ElementOrm.state == state.value)
                .all()
        ]

    def get_sub_elems_by_id(self, sub_id, *, offset=0, limit=None, state=Element.State.Unconsumed, gte_s3_key=None):
        query = self._db \
            .query(ElementOrm) \
            .filter(ElementOrm.sub_id == sub_id) \
            .filter(ElementOrm.state == state.value) \
            .limit(limit) \
            .offset(offset)

        if gte_s3_key is not None:
            query = query.filter(ElementOrm.key >= gte_s3_key)

        return [
            Element(orm)
            for orm in query.all()
        ]

    def get_batch_elems(self, sub_id, batch_id, *, offset=0, limit=None, gte_s3_key=None):
        query = self._db \
            .query(ElementOrm) \
            .filter(ElementOrm.sub_id == sub_id) \
            .filter(ElementOrm.state == Element.State.Batched.value) \
            .filter(ElementOrm.batch_id == batch_id) \
            .limit(limit) \
            .offset(offset)

        if gte_s3_key is not None:
            query = query.filter(ElementOrm.key >= gte_s3_key)

        return [
            Element(orm)
            for orm in query.all()
        ]

    def get_active_batch_id(self, sub_id):
        return self._db \
            .query(ElementOrm.batch_id) \
            .filter(ElementOrm.sub_id == sub_id) \
            .filter(ElementOrm.state == Element.State.Batched.value) \
            .group_by(ElementOrm.batch_id) \
            .order_by(ElementOrm.created) \
            .first()
