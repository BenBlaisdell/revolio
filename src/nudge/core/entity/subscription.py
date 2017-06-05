import abc
import enum
import re
import uuid

import revolio as rv
import sqlalchemy as sa

from nudge.core.entity import EntityOrm


class SubscriptionEndpointProtocol(enum.Enum):
    SQS = 'SQS'


class SubscriptionEndpoint(rv.Serializable):

    Protocol = SubscriptionEndpointProtocol

    @staticmethod
    def deserialize(data):
        if data is None:
            return None

        protocol = SubscriptionEndpoint.Protocol[data['Protocol']]
        params = data['Parameters']

        if protocol == SubscriptionEndpoint.Protocol.SQS:
            return SqsEndpoint.deserialize(params)

    @abc.abstractmethod
    def send_message(self, ctx, msg):
        pass


class SqsEndpoint(SubscriptionEndpoint):

    def __init__(self, queue_url):
        super(SqsEndpoint, self).__init__()
        self._queue_url = queue_url

    def serialize(self):
        return {
            'Protocol': 'SQS',
            'Parameters': {
                'QueueUrl': self._queue_url,
            },
        }

    @staticmethod
    def deserialize(data):
        return None if (data is None) else SqsEndpoint(
            queue_url=data['QueueUrl'],
        )

    def send_message(self, ctx, msg):
        ctx.sqs.send_message(
            QueueUrl=self._queue_url,
            MessageBody=msg,
        )


# 0 byte threshold
# every file creates a new batch
DEFAULT_THRESHOLD = 0


class SubscriptionTrigger(rv.Serializable):
    """Describes the conditions under which a batch is created and the endpoint that is notified."""

    Endpoint = SubscriptionEndpoint

    @property
    def endpoint(self):
        return self._endpoint

    @property
    def threshold(self):
        return self._threshold

    @property
    def custom(self):
        return self._custom

    def __init__(self, endpoint, *, threshold=DEFAULT_THRESHOLD, custom=None):
        super().__init__()
        self._endpoint = endpoint
        self._threshold = threshold
        self._custom = custom

    def serialize(self):
        return {
            'Endpoint': self._endpoint.serialize(),
            'Threshold': self._threshold,
            'Custom': self._custom,
        }

    @staticmethod
    def deserialize(data):
        return None if (data is None) else SubscriptionTrigger(
            endpoint=SubscriptionTrigger.Endpoint.deserialize(data.get('Endpoint', None)),
            threshold=data.get('Threshold', DEFAULT_THRESHOLD),
            custom=data.get('Custom', None),
        )


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

    Trigger = SubscriptionTrigger

    @property
    def trigger(self):
        return Subscription.Trigger.deserialize(self._orm.data['trigger'])

    @trigger.setter
    def trigger(self, trigger):
        assert isinstance(trigger, Subscription.Trigger)
        self._orm.data['trigger'] = trigger.serialize()

    @staticmethod
    def create(bucket, *, prefix=None, regex=None, trigger=None):
        return Subscription(SubscriptionOrm(
            id=str(uuid.uuid4()),
            state=Subscription.State.Active.value,
            bucket=bucket,
            prefix=prefix,
            data=dict(
                regex=regex,
                trigger=trigger.serialize() if (trigger is not None) else None,
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


# orm


class SubscriptionOrm(EntityOrm):
    __tablename__ = 'subscription'

    id = sa.Column(sa.String, primary_key=True)
    state = sa.Column(sa.String)
    bucket = sa.Column(sa.String)
    prefix = sa.Column(sa.String)


# service


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
