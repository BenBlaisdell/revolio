import enum
import uuid

from nudge.entity.entity import Entity
from nudge.orm import ElementOrm


class ElementService:

    def __init__(self, session):
        self._session = session


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
    def time(self):
        return self._time

    def __init__(self, id, state, sub_id, bucket, key, size, time):
        super(Element, self).__init__()
        self._id = id
        self._state = state
        self._sub_id = sub_id
        self._bucket = bucket
        self._key = key
        self._size = size
        self._time = time

    def to_orm(self):
        return ElementOrm(
            id=self._id,
            state=self._state,
            sub_id=self._sub_id,
            data=dict(
                bucket=self._bucket,
                key=self._key,
                size=self._size,
                time=self._time,
            ),
        )

    @staticmethod
    def from_orm(orm):
        return Element(
            id=orm.id,
            state=ElementState[orm.state],
            sub_id=orm.subscription,
            bucket=orm.bucket,
            key=orm.data['key'],
            size=orm.data['size'],
            time=orm.data['time'],
        )

    @staticmethod
    def create(sub_id, bucket, key, size, time):
        return Element(
            id=str(uuid.uuid4()),
            state=ElementState.UNCONSUMED,
            sub_id=sub_id,
            bucket=bucket,
            key=key,
            size=size,
            time=time,
        )


class ElementState(enum.Enum):
    UNCONSUMED = 'UNCONSUMED'
    SENT = 'SENT'
    CONSUMED = 'CONSUMED'
