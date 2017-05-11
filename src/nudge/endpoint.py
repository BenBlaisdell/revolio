import abc
import enum

from nudge.util import Serializable


class EndpointProtocol(enum.Enum):
    Sqs = 'Sqs'


class Endpoint(Serializable):

    def serialize(self):
        pass

    @classmethod
    def deserialize(cls, data):
        protocol = EndpointProtocol[data['Protocol']]
        params = data['Parameters']

        if protocol == EndpointProtocol.Sqs:
            return SqsEndpoint.deserialize(params)

    @abc.abstractmethod
    def send_message(self, ctx, msg):
        pass


class SqsEndpoint(Endpoint):

    def __init__(self, ctx, queue_url):
        super(SqsEndpoint, self).__init__()
        self._queue_url = queue_url
        self._ctx = ctx

    @classmethod
    def deserialize(cls, data):
        return cls(queue_url=data['QueueUrl'])

    def send_message(self, ctx, msg):
        ctx.sqs.send_message(
            QueueUrl=self._queue_url,
            MessageBody=msg,
        )
