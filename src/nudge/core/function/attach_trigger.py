import logging

import revolio as rv
import revolio.serializable
from revolio.function import validate
from revolio.sqlalchemy import autocommit

from nudge.core.entity.subscription import Subscription
from nudge.core.entity.subscription.trigger import SubscriptionTrigger


_log = logging.getLogger(__name__)


class AttachTrigger(rv.function.Function):

    def __init__(self, ctx, db, sub_srv):
        super().__init__(ctx)
        self._db = db
        self._sub_srv = sub_srv

    def format_request(self, sub_id, trigger):
        return {
            'SubscriptionId': sub_id,
            'Trigger': trigger.serialize(),
        }

    @validate(
        subscription_id=rv.serializable.fields.Str(),
        trigger=rv.serializable.fields.Nested(SubscriptionTrigger),
    )
    def handle_request(self, request):

        # make call

        batch = self(
            sub_id=request.subscription_id,
            trigger=request.trigger,
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
            _log.info(f'{sub} is backfilling and will be evaluated when complete')
            return None

        return self._sub_srv.evaluate(sub)
