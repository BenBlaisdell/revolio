import enum
import uuid

import marshmallow as mm
import sqlalchemy as sa
from nudge.endpoint import Endpoint

from nudge.entity.entity import Entity
from nudge.orm import SubscriptionOrm
from nudge.util import Serializable


class SubscriptionService:

    def __init__(self, session):
        super(SubscriptionService, self).__init__()
        self._session = session

    def deactivate(self, sub_id):
        success = self._session \
            .query(SubscriptionOrm) \
            .filter(SubscriptionOrm.id == sub_id) \
            .update(state=SubscriptionState.Inactive.value)

        if not success:
            raise Exception('No subscription with id {}'.format(sub_id))

    def find_matching_subscriptions(self, bucket, key):
        return [
            Subscription.from_orm(orm)
            for orm in self._session
                .query(SubscriptionOrm)
                .filter(SubscriptionOrm.bucket == bucket)
                .filter(sa.sql.expression.bindparam('k', key).startswith(SubscriptionOrm.prefix))
                .all()
        ]

    def get_sub(self, sub_id):
        return self._session \
            .query(SubscriptionOrm) \
            .get(sub_id)


class Subscription(Entity):

    @property
    def id(self):
        return self._id

    @property
    def state(self):
        return self._state

    @property
    def bucket(self):
        return self._bucket

    @property
    def prefix(self):
        return self._prefix

    @property
    def regex(self):
        return self._regex

    @property
    def threshold(self):
        return self._threshold

    @property
    def endpoint(self):
        return self._endpoint

    @staticmethod
    def create(bucket, endpoint, *, prefix=None, regex=None, threshold=0):
        return Subscription(
            id=str(uuid.uuid4()),
            state=SubscriptionState.Active,
            bucket=bucket,
            prefix=prefix,
            regex=regex,
            threshold=threshold,
            endpoint=Endpoint.deserialize(endpoint),
        )

    def __init__(self, id, state, bucket, prefix, regex, threshold, endpoint):
        super(Subscription, self).__init__()
        self._id = id
        self._state = state
        self._bucket = bucket
        self._prefix = prefix
        self._regex = regex
        self._threshold = threshold
        self._endpoint = endpoint

    def to_orm(self):
        return SubscriptionOrm(
            id=self._id,
            state=self._state.value,
            bucket=self._bucket,
            prefix=self._prefix,
            data=dict(
                regex=self._regex,
                threshold=self._threshold,
                endpoint=self._endpoint.serialize(),
            )
        )

    @staticmethod
    def from_orm(orm):
        return Subscription(
            id=orm.id,
            state=orm.state,
            bucket=orm.bucket,
            prefix=orm.prefix,
            regex=orm.data['regex'],
            threshold=orm.data['threshold'],
            endpoint=Endpoint.deserialize(orm.data['endpoint']),
        )


class SubscriptionState(enum.Enum):
    Active = 'Active'
    Inactive = 'Inactive'


# schema


class SubscriptionEndpointSchema(mm.Schema):
    Protocol = mm.fields.Str()
    Params = mm.fields.Dict()


class SubscriptionSchema(mm.Schema):
    id = mm.fields.UUID(
        required=True,
    )

    state = mm.fields.Str(
        required=True,
    )

    bucket = mm.fields.Str(
        required=True,
    )

    prefix = mm.fields.Str(
        default=None,
    )

    regex = mm.fields.Str(
        default=None,
        help=' '.join([
            'The regular expression against which',
            'the remainder of the key is matched.',
            'Syntax follows that of the python re package.',
        ]),
    )

    threshold = mm.fields.Int(
        default=0,
        help='The byte threshold at which a subscription batch is created',
    )

    endpoint = mm.fields.Nested(
        SubscriptionEndpointSchema(),
    )

    @mm.post_load
    def return_subscription_entity(self, data):
        return Subscription(**data)
