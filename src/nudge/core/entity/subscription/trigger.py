import revolio as rv

from nudge.core.entity.subscription.endpoint import SubscriptionEndpoint, SubscriptionEndpointProtocol


class SubscriptionTrigger(rv.Serializable):
    """The conditions under which a batch is created and the endpoint that is notified."""

    Endpoint = SubscriptionEndpoint
    endpoint = rv.serializable.fields.ObjectEnum(
        SubscriptionEndpointProtocol,
        optional=True,
        type_field='protocol',
    )

    threshold = rv.serializable.fields.Int(
        # 0 byte threshold
        # every file creates a new batch
        optional=True,
        default=0,
    )

    custom = rv.serializable.fields.Str(
        optional=True,
    )
