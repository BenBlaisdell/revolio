import revolio as rv
import revolio.util.uuid

from nudge.core.entity.subscription.service import SubscriptionService
from nudge.core.entity.subscription.endpoint import SubscriptionEndpoint, SubscriptionEndpointProtocol


class SubscriptionTrigger(rv.Serializable):
    """The conditions under which a batch is created and the endpoint that is notified."""

    Endpoint = SubscriptionEndpoint
    endpoint = rv.serializable.fields.ObjectEnum(
        SubscriptionEndpointProtocol,
        help='The endpoint where batch notification messages will be sent.',
        optional=True,
        type_field='protocol',
    )

    threshold = rv.serializable.fields.Int(
        # 0 byte threshold
        # every file creates a new batch
        help='The number of bytes required for a subscription to create a new batch.',
        optional=True,
        default=0,
    )

    custom = rv.serializable.fields.Str(
        help='\n'.join([
            'A serialized JSON object that will be deserialized and sent in place of the default batch notification message.',
            'If not supplied, the message will be in the form:',
            SubscriptionService.get_default_ping_data(sub_id=rv.util.uuid.dummy_uuid),
        ]),
        optional=True,
    )
