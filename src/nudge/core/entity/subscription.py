import abc
import enum
import json
import logging
import re
import uuid

import revolio as rv
import revolio.sqlalchemy.types
import sqlalchemy as sa

from nudge.core.entity import Entity, Batch, Element


_log = logging.getLogger(__name__)


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


class SubscriptionState(enum.Enum):
    BACKFILLING = 'BACKFILLING'
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'


class Subscription(Entity):
    __tablename__ = 'subscription'

    id = sa.Column(
        sa.String,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
        primary_key=True,
    )

    State = SubscriptionState
    state = sa.Column(
        sa.Enum(State),
        default=State.ACTIVE,
        nullable=False,
    )

    bucket = sa.Column(
        sa.String,
        nullable=False,
    )

    prefix = sa.Column(
        sa.String,
        nullable=True
    )

    regex = sa.Column(
        rv.sqlalchemy.types.Regex,
        nullable=True,
    )

    Trigger = SubscriptionTrigger

    trigger = sa.Column(
        rv.serializable.column_type(SubscriptionTrigger),
        nullable=True,
    )

    def __repr__(self):
        return super().__repr__(id=self.id)


# service


class SubscriptionService:

    def __init__(self, ctx, db, elem_srv):
        super(SubscriptionService, self).__init__()
        self._ctx = ctx
        self._db = db
        self._elem_srv = elem_srv

    @staticmethod
    def get_ping_data(sub):
        return json.loads(sub.trigger.custom) if (sub.trigger.custom is not None) else {'SubscriptionId': sub.id}


    @staticmethod
    def matches(sub, bucket, key):
        return all([
            bucket == sub.bucket,
            key.startswith(sub.prefix),
            (sub.regex is None) or sub.regex.match(key[len(sub.prefix):]),
        ])

    def get_subscription(self, sub_id):
        return self._db \
            .query(Subscription) \
            .get(sub_id)

    def find_matching_subscriptions(self, bucket, key):
        query = self._db \
            .query(Subscription) \
            .filter(Subscription.state == Subscription.State.ACTIVE.value) \
            .filter(Subscription.bucket == bucket) \

        k = sa.sql.expression.bindparam('k', key)
        query = query \
            .filter(k.startswith(Subscription.prefix))

        subs = list(filter(lambda s: self.matches(s, bucket, key), query.all()))

        _log.debug('Found subscriptions matching bucket="{b}" key="{k}": {s}'.format(
            b=bucket,
            k=key,
            s=subs,
        ))

        return subs

    def evaluate(self, sub):
        _log.info('Evaluating {}'.format(sub))

        if sub.trigger is None:
            _log.info('No trigger attached')
            return

        elems = self._elem_srv.get_sub_elems(sub.id, state=Element.State.AVAILABLE)
        if _batch_size(elems) >= sub.trigger.threshold:
            _log.info('{s} has passed threshold of {t} with elements {e}'.format(
                s=sub, t=sub.trigger.threshold, e=elems,
            ))
            return self._create_and_send_batch(sub, elems)

        _log.info('{s} not ready to batch')
        return None

    def _create_and_send_batch(self, sub, elems):
        batch = self._db.add(Batch(
            sub_id=sub.id,
            state=Batch.State.UNCONSUMED,
        ))

        for elem in elems:
            assert elem.sub_id == sub.id
            assert elem.state == Element.State.AVAILABLE
            elem.state = Element.State.BATCHED
            elem.batch_id = batch.id

        self._db.flush()

        if sub.trigger.endpoint is not None:
            _log.info('Sending {} trigger message'.format(sub))
            sub.trigger.endpoint.send_message(
                ctx=self._ctx,
                msg=self.get_ping_data(sub),
            )

        return batch

    def assert_active(self, sub):
        if sub.state is not Subscription.State.ACTIVE:
            raise Exception('Subscription state is {}'.format(sub.state.value))


def _batch_size(elems):
    return sum(e.size for e in elems)
