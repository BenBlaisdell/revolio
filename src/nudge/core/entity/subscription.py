import enum
import re
import uuid

import marshmallow as mm
import revolio as rv
import sqlalchemy as sa

from nudge.core.endpoint import Endpoint
from nudge.core.orm import SubscriptionOrm


class Subscription(rv.Entity):

    @property
    def id(self):
        return self._orm.id

    class State(enum.Enum):
        Backfilling = 'Backfilling'
        Active = 'Active'
        Inactive = 'Inactive'

    @property
    def state(self):
        return Subscription.State[self._orm.state]

    @state.setter
    def state(self, state):
        assert isinstance(state, Subscription.State)
        self._orm.state = state.value

    @property
    def bucket(self):
        return self._orm.bucket

    @property
    def prefix(self):
        return self._orm.prefix

    @property
    def regex(self):
        r = self._orm.data.get('regex', None)
        return re.compile(r'\A{}\Z'.format(r)) if (r is not None) else None

    @property
    def threshold(self):
        return int(self._orm.data['threshold'])

    @property
    def endpoint(self):
        return Endpoint.deserialize(self._orm.data['endpoint'])

    @property
    def custom(self):
        return self._orm.data.get('custom', None)

    @staticmethod
    def create(bucket, endpoint, *, prefix=None, regex=None, threshold=0, custom=None):
        return Subscription(SubscriptionOrm(
            id=str(uuid.uuid4()),
            state=Subscription.State.Active.value,
            bucket=bucket,
            prefix=prefix,
            data=dict(
                regex=regex,
                threshold=threshold,
                endpoint=endpoint.serialize(),
                custom=custom,
            )
        ))

    def matches(self, bucket, key):
        return all([
            bucket == self.bucket,
            key.startswith(self.prefix),
            (self.regex is None) or self.regex.match(key[len(self.prefix):]),
        ])

    def __str__(self):
        return super().__str__(
            id=self.id,
            state=self.state,
        )


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

    metadata = mm.fields.Dict(
        default=None,
        help=' '.join(['The custom json response agreed upon'
                       'on creation of subscription entity. This'
                       'custom response replaces the default nudge'
                       'message on the target endpoint/queue.'])
    )

    @mm.post_load
    def return_subscription_entity(self, data):
        return Subscription.create(**data)


class SubscriptionService:

    def __init__(self, db, log):
        super(SubscriptionService, self).__init__()
        self._db = db
        self._log = log

    def get_subscription(self, sub_id):
        orm = self._db \
            .query(SubscriptionOrm) \
            .get(sub_id)

        if orm is None:
            raise Exception('No subscription with id {}'.format(sub_id))

        sub = Subscription(orm)
        self._log.debug('Found {} by id'.format(sub))
        return sub

    def find_matching_subscriptions(self, bucket, key):
        subs = [
            Subscription(orm)
            for orm in self._db
                .query(SubscriptionOrm)
                .filter(SubscriptionOrm.bucket == bucket)
                .filter(sa.sql.expression.bindparam('k', key).startswith(SubscriptionOrm.prefix))
                .all()
        ]

        subs = filter(lambda s: s.matches(bucket, key), subs)
        self._log.debug('Found subscriptions matching bucket="{b}" key="{k}": {s}'.format(
            b=bucket,
            k=key,
            s=subs,
        ))

        return subs
