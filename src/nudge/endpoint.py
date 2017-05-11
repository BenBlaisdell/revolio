import abc
import enum

from nudge.util import Serializable


class EndpointProtocol(enum.Enum):
    SQS = 'SQS'


class Endpoint(Serializable):

    def serialize(self):
        pass

    @classmethod
    def deserialize(cls, data):
        protocol = EndpointProtocol[data['Protocol']]
        params = data['Parameters']

        if protocol == EndpointProtocol.SQS:
            return SqsEndpoint.deserialize(params)

    @abc.abstractmethod
    def send_message(self, ctx, msg):
        pass


class SqsEndpoint(Endpoint):

    def __init__(self, queue_url):
        super(SqsEndpoint, self).__init__()
        self._queue_url = queue_url

    @classmethod
    def deserialize(cls, data):
        return cls(queue_url=data['QueueUrl'])

    def send_message(self, ctx, msg):
        ctx.sqs.send_message(
            QueueUrl=self._queue_url,
            MessageBody=msg,
        )
