import abc
import enum
import uuid

import boto3
from cached_property import cached_property

from nudge.db import SubscriptionOrm
from nudge.entity.entity import Entity
from nudge.util import Serializable


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

    def __init__(self, id, state, bucket, prefix, regex, threshold, endpoint):
        super(Subscription, self).__init__()
        self._id = id
        self._state = state
        self._bucket = bucket
        self._prefix = prefix
        self._regex = regex
        self._threshold = threshold
        self._endpoint = endpoint

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


# endpoint


class EndpointProtocol(enum.Enum):
    Sqs = 'Sqs'


class Endpoint(Serializable):

    def serialize(self):
        pass

    @staticmethod
    def deserialize(data):
        protocol = EndpointProtocol[data['Protocol']]
        params = data['Parameters']

        if protocol == EndpointProtocol.Sqs:
            return SqsEndpoint.deserialize(params)

    @abc.abstractmethod
    def send_message(self, msg):
        pass


class SqsEndpoint(Endpoint):

    def __init__(self, queue_url):
        super(SqsEndpoint, self).__init__()
        self._queue_url = queue_url

    @staticmethod
    def deserialize(data):
        return SqsEndpoint(queue_url=data['QueueUrl'])

    @cached_property
    def _client(self):
        return boto3.cilent('sqs')

    def send_message(self, msg):
        self._client.send_message(
            QueueUrl=self._queue_url,
            MessageBody=msg,
        )