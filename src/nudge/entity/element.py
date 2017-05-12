import datetime as dt
import enum
import uuid

from nudge.entity.entity import Entity
from nudge.orm import ElementOrm


class ElementService:

    def __init__(self, session):
        self._session = session

    def get_elements(self, elem_ids):
        elems = [
            Element(orm)
            for orm in self._session
                .query(ElementOrm)
                .filter(ElementOrm.id.in_(elem_ids))
                .all()
        ]

        assert len(elems) == len(elem_ids)
        return elems

    def get_sub_elems(self, sub):
        return [
            Element(orm)
            for orm in self._session
                .query(ElementOrm)
                .filter(ElementOrm.sub_id == sub.id)
                .all()
        ]

    def mark_consumed(self, elem):
        pass


class ElementState(enum.Enum):
    Unconsumed = 'Unconsumed'
    Sent = 'Sent'
    Consumed = 'Consumed'


class Element(Entity):

    State = ElementState

    @property
    def id(self):
        return self._orm.id

    @property
    def state(self):
        return ElementState[self._orm.state]

    @state.setter
    def state(self, state):
        assert isinstance(state, ElementState)
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
            state=ElementState.Unconsumed.value,
            sub_id=sub_id,
            data=dict(
                bucket=bucket,
                key=key,
                size=size,
                created=created,
            )
        ))
