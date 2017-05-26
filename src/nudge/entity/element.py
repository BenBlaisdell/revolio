import datetime as dt
import enum
import uuid

from nudge.entity.entity import Entity
from nudge.orm import ElementOrm


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

    def get_sub_elems(self, sub):
        return [
            Element(orm)
            for orm in self._db
                .query(ElementOrm)
                .filter(ElementOrm.sub_id == sub.id)
                .all()
        ]

    def get_sub_elems_by_id(self, sub_id):
        return [
            Element(orm)
            for orm in self._db
                .query(ElementOrm)
                .filter(ElementOrm.sub_id == sub_id)
                .all()
        ]


class Element(Entity):

    @property
    def id(self):
        return self._orm.id

    class State(enum.Enum):
        Unconsumed = 'Unconsumed'
        Sent = 'Sent'
        Consumed = 'Consumed'

    @property
    def state(self):
        return Element.State[self._orm.state]

    @state.setter
    def state(self, state):
        assert isinstance(state, Element.State)
        self._orm.state = state.value

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
    def created(self):
        return dt.datetime.strptime(self._orm.data['created'], '%Y-%m-%d %H:%M:%S')

    @staticmethod
    def create(sub_id, bucket, key, size, created):
        return Element(ElementOrm(
            id=str(uuid.uuid4()),
            state=Element.State.Unconsumed.value,
            sub_id=sub_id,
            data=dict(
                bucket=bucket,
                key=key,
                size=size,
                created=dt.datetime.strftime(created, '%Y-%m-%d %H:%M:%S'),
            )
        ))
