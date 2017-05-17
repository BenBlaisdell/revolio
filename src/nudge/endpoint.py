import abc
import enum

from nudge.util import Serializable


class EndpointProtocol(enum.Enum):
    SQS = 'SQS'


class Endpoint(Serializable):

    @classmethod
    def deserialize(cls, data):
        protocol = EndpointProtocol[data['Protocol']]
        params = data['Parameters']

        if protocol == EndpointProtocol.SQS:
            return SqsEndpoint.deserialize(params)

    @abc.abstractmethod
    def send_message(self, ctx, msg):
        pass

    @abc.abstractmethod
    def receive_message(self, ctx, wait_time):
        pass


class SqsEndpoint(Endpoint):

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

    @classmethod
    def deserialize(cls, data):
        return cls(queue_url=data['QueueUrl'])

    def send_message(self, ctx, msg):
        ctx.sqs.send_message(
            QueueUrl=self._queue_url,
            MessageBody=msg,
        )

    def receive_message(self, ctx, *, max_messages=1, wait_time=20):
        response = ctx.sqs.receive_message(
            QueueUrl=self._queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=wait_time
        )
        return response.get('Messages')

    def delete_message(self, ctx, receipt_handle):
        ctx.sqs.delete_message(
            QueueUrl=self._queue_url,
            ReceiptHandle=receipt_handle
        )
