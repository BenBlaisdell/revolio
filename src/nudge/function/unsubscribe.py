from nudge.entity.subscription import SubscriptionState


class Unsubscribe:

    def __init__(self, db, sub_srv):
        self._db = db
        self._sub_srv = sub_srv

    def __call__(self, sub_id):
        sub = self._sub_srv.get_subscription(sub_id)
        assert sub.state == SubscriptionState.Active
        sub.state = SubscriptionState.Inactive
        self._db.commit()
