import enum
import uuid

from nudge.entity.entity import Entity
from nudge.orm import ElementOrm


class Element(Entity):

    @property
    def id(self):
        return self._id

    @property
    def state(self):
        return self._state

    @property
    def subscription(self):
        return self._subscription

    def __init__(self, id, state, bucket, key, subscription):
        super(Element, self).__init__()
        self._id = id
        self._state = state
        self._bucket = bucket
        self._key = key
        self._subscription = subscription

    def to_orm(self):
        return ElementOrm(
            id=self._id,
            state=self._state,
            bucket=self._bucket,
            key=self._key,
            subscription=self._subscription,
        )

    @staticmethod
    def from_orm(orm):
        return Element(
            id=orm.id,
            state=ElementState[orm.state],
            bucket=orm.bucket,
            key=orm.key,
            subscription=orm.subscription,
        )

    @staticmethod
    def create(subscription_id, bucket, key):
        return Element(
            id=str(uuid.uuid4()),
            state=ElementState.UNCONSUMED,
            bucket=bucket,
            key=key,
            subscription=subscription_id,
        )


class ElementState(enum.Enum):
    UNCONSUMED = 'UNCONSUMED'
    SENT = 'SENT'
    CONSUMED = 'CONSUMED'
