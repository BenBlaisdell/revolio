import revolio as rv

from nudge.core.entity.subscription import SubscriptionTrigger, Subscription


class AttachTrigger(rv.Function):

    def __init__(self, ctx, db, sub_srv, log):
        super().__init__(ctx)
        self._db = db
        self._sub_srv = sub_srv
        self._log = log

    def format_request(self, sub_id, trigger):
        return {
            'SubscriptionId': sub_id,
            'Trigger': trigger.serialize(),
        }

    def handle_request(self, request):
        sub_id = request['SubscriptionId']
        assert isinstance(sub_id, str)

        trigger = SubscriptionTrigger.deserialize(request.get('Trigger', {}))
        assert isinstance(trigger, SubscriptionTrigger)

        # make call

        batch = self(
            sub_id=sub_id,
            trigger=trigger,
        )

        # format response

        return {
            'BatchId': batch.id if (batch is not None) else None,
        }

    def __call__(self, sub_id, trigger):
        sub = self._sub_srv.get_subscription(sub_id)
        self._sub_srv.assert_active(sub)

        if sub.trigger is not None:
            raise Exception('Subscription already has a trigger')

        sub.trigger = trigger

        batch = self._sub_srv.evaluate(sub)

        self._db.commit()

        return batch
