import abc
import enum
import json
import re
import uuid

import revolio as rv
from revolio.serializable import KeyFormat
import sqlalchemy as sa

from nudge.core.entity import Orm, Batch, Element


class SubscriptionEndpointProtocol(enum.Enum):
    SQS = 'SQS'


class SubscriptionEndpoint(rv.Serializable):

    Protocol = SubscriptionEndpointProtocol

    @staticmethod
    def _deserialize(data):
        protocol = SubscriptionEndpoint.Protocol[data['Protocol']]
        params = data['Parameters']

        if protocol == SubscriptionEndpoint.Protocol.SQS:
            return SqsEndpoint.deserialize(params)

    @abc.abstractmethod
    def send_message(self, ctx, msg):
        """
        
        :type msg: dict
        """
        pass


class SqsEndpoint(SubscriptionEndpoint):

    def __init__(self, queue_url):
        super(SqsEndpoint, self).__init__()
        self._queue_url = queue_url

    def _serialize(self):
        return {
            'Protocol': 'SQS',
            'Parameters': {
                'QueueUrl': self._queue_url,
            },
        }

    @staticmethod
    def _deserialize(data):
        return SqsEndpoint(
            queue_url=data['QueueUrl'],
        )

    def send_message(self, ctx, msg):
        ctx.sqs.send_message(
            QueueUrl=self._queue_url,
            MessageBody=json.dumps(msg),
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

    def _serialize(self):
        return {
            'Endpoint': self._endpoint.serialize(),
            'Threshold': self._threshold,
            'Custom': self._custom,
        }

    @staticmethod
    def _deserialize(data):
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
        BACKFILLING = 'BACKFILLING'
        ACTIVE = 'ACTIVE'
        INACTIVE = 'INACTIVE'

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

    @property
    def subscriber_ping_data(self):
        return self.trigger.custom if (self.trigger.custom is not None) else {'SubscriptionId': self.id}

    @staticmethod
    def create(bucket, *, prefix=None, regex=None, trigger=None):
        return Subscription(SubscriptionOrm(
            id=str(uuid.uuid4()),
            state=Subscription.State.ACTIVE.value,
            bucket=bucket,
            prefix=prefix,
            data=dict(
                regex=regex,
                trigger=trigger.serialize(key_format=KeyFormat.Snake) if (trigger is not None) else None,
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


class SubscriptionOrm(Orm):
    __tablename__ = 'subscription'

    id = sa.Column(sa.String, primary_key=True)
    state = sa.Column(sa.String)
    bucket = sa.Column(sa.String)
    prefix = sa.Column(sa.String)


# service


class SubscriptionService:

    def __init__(self, ctx, db, log, elem_srv):
        super(SubscriptionService, self).__init__()
        self._ctx = ctx
        self._db = db
        self._log = log
        self._elem_srv = elem_srv

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
        query = self._db \
            .query(SubscriptionOrm) \
            .filter(SubscriptionOrm.bucket == bucket)

        # escape to prevent '_' or '%' from matching characters
        k = sa.sql.expression.bindparam('k', key)
        query = query \
            .filter(k.startswith(SubscriptionOrm.prefix))

        subs = [Subscription(orm) for orm in query.all()]
        subs = filter(lambda s: s.matches(bucket, key), subs)

        self._log.debug('Found subscriptions matching bucket="{b}" key="{k}": {s}'.format(
            b=bucket,
            k=key,
            s=subs,
        ))

        return subs

    def evaluate(self, sub):
        if sub.trigger is None:
            return

        elems = self._elem_srv.get_sub_elems(sub.id, state=Element.State.AVAILABLE)
        if _batch_size(elems) >= sub.trigger.threshold:
            return self._create_and_send_batch(sub, elems)

        return None

    def _create_and_send_batch(self, sub, elems):
        batch = self._db.add(Batch.create(sub.id))

        for elem in elems:
            assert elem.sub_id == sub.id
            assert elem.state == Element.State.AVAILABLE
            elem.state = Element.State.BATCHED
            elem.batch_id = batch.id

        self._db.flush()

        if sub.trigger.endpoint is None:
            return

        sub.trigger.endpoint.send_message(
            ctx=self._ctx,
            msg=sub.subscriber_ping_data,
        )

        return batch


def _batch_size(elems):
    return sum(e.size for e in elems)
