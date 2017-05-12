import datetime as dt
import enum
import uuid

from nudge.entity.entity import Entity
from nudge.orm import ElementOrm


class ElementService:

    def __init__(self, session):
        self._session = session

    def get_elements(self, elem_ids):
        return [
            Element.from_orm(orm)
            for orm in self._session
                .query(ElementOrm)
                .filter()
        ]

    def get_sub_elems(self, sub_id):
        return [
            Element.from_orm(orm)
            for orm in self._session
                .query(ElementOrm)
                .filter(ElementOrm.sub_id == sub_id)
                .all()
        ]

    def mark_consumed(self, elem):
        pass


class Element(Entity):

    @property
    def id(self):
        return self._id

    @property
    def state(self):
        return self._state

    @property
    def sub_id(self):
        return self._sub_id

    @property
    def bucket(self):
        return self._bucket

    @property
    def key(self):
        return self._key

    @property
    def size(self):
        return self._size

    @property
    def created(self):
        return self._created

    def __init__(self, id, state, sub_id, bucket, key, size, created):
        super(Element, self).__init__()
        self._id = id
        self._state = state
        self._sub_id = sub_id
        self._bucket = bucket
        self._key = key
        self._size = size
        self._created = created

    def to_orm(self):
        return ElementOrm(
            id=self._id,
            state=self._state.value,
            sub_id=self._sub_id,
            data=dict(
                bucket=self._bucket,
                key=self._key,
                size=self._size,
                created=self._created,
            ),
        )

    @staticmethod
    def from_orm(orm):
        return Element(
            id=orm.id,
            state=ElementState[orm.state],
            sub_id=orm.sub_id,
            bucket=orm.data['bucket'],
            key=orm.data['key'],
            size=int(orm.data['size']),
            created=dt.datetime.strptime(orm.data['created'], '%Y-%m-%d %H:%M:%S'),
        )

    @staticmethod
    def create(sub_id, bucket, key, size, created):
        return Element(
            id=str(uuid.uuid4()),
            state=ElementState.Unconsumed,
            sub_id=sub_id,
            bucket=bucket,
            key=key,
            size=size,
            created=created,
        )


class ElementState(enum.Enum):
    Unconsumed = 'Unconsumed'
    Sent = 'Sent'
    Consumed = 'Consumed'
