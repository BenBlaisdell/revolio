import revolio as rv

from nudge.core.util import autocommit


class GetSubscription(rv.Function):

    def __init__(self, ctx, sub_srv):
        super().__init__(ctx)
        self._sub_srv = sub_srv

    def format_request(self, sub_id):
        return {
            'SubscriptionId': sub_id,
        }

    def handle_request(self, request):
        sub_id = request['SubscriptionId']
        assert isinstance(sub_id, str)

        # make call

        sub = self(
            sub_id=sub_id,
        )

        # format response

        return {
            'Id': sub.id,
            'State': sub.state.value,
            'Bucket': sub.bucket,
            'Prefix': sub.prefix,
            'Regex': sub.regex,
            'Trigger': sub.trigger.serialize() if (sub.trigger is not None) else None,
        }

    @autocommit
    def __call__(self, sub_id):
        return self._sub_srv.get_subscription(
            sub_id=sub_id,
        )
