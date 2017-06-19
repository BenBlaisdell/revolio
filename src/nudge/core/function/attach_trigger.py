import logging

import revolio as rv

from nudge.core.entity.subscription import SubscriptionTrigger, Subscription
from nudge.core.util import autocommit


_log = logging.getLogger(__name__)


class AttachTrigger(rv.Function):

    def __init__(self, ctx, db, sub_srv):
        super().__init__(ctx)
        self._db = db
        self._sub_srv = sub_srv

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

    @autocommit
    def __call__(self, sub_id, trigger):
        sub = self._sub_srv.get_subscription(sub_id)

        if sub.state is Subscription.State.INACTIVE:
            raise Exception('Subscription has been deactivated')

        if sub.trigger is not None:
            raise Exception('Subscription already has a trigger')

        sub.trigger = trigger

        if sub.state is Subscription.State.BACKFILLING:
            _log.info('{} is backfilling and will be evaluated when complete'.format(sub))
            return None

        return self._sub_srv.evaluate(sub)
