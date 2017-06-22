import enum

import revolio as rv


class SubscriptionEndpoint(rv.serializable.Serializable):
    """Base endpoint class."""
    pass


class SqsEndpoint(SubscriptionEndpoint):
    """Endpoint as an AWS SQS Queue."""
    queue_url = rv.serializable.fields.Str()


class SubscriptionEndpointProtocol(enum.Enum):
    """Enum of valid endpoints."""
    SQS = SqsEndpoint
