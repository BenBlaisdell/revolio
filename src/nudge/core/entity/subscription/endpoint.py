import abc
import enum
import json

import revolio as rv


class SubscriptionEndpoint(rv.serializable.Serializable):
    """Base endpoint class."""

    @abc.abstractmethod
    def send_message(self, ctx, msg):
        pass


class SqsEndpoint(SubscriptionEndpoint):
    """Endpoint as an AWS SQS Queue."""

    queue_url = rv.serializable.fields.Str()

    def send_message(self, ctx, msg):
        ctx.sqs.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps(msg),
        )


class SubscriptionEndpointProtocol(enum.Enum):
    """Enum of valid endpoints."""
    SQS = SqsEndpoint
