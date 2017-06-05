import revolio as rv

from nudge.core.entity.subscription import SubscriptionTrigger


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
        self._log.info('Handling request: AttachTrigger')

        # parse parameters

        sub_id = request['SubscriptionId']
        assert isinstance(sub_id, str)

        trigger = SubscriptionTrigger.deserialize(request.get('Trigger', {}))
        assert isinstance(trigger, SubscriptionTrigger)

        # make call

        self(
            sub_id=sub_id,
            trigger=trigger,
        )

        # format response

        return {'Message': 'Success'}

    def __call__(self, sub_id, trigger):
        self._log.info('Handling call: AttachTrigger')

        sub = self._sub_srv.get_subscription(sub_id)
        sub.trigger = trigger

        self._db.commit()
