from nudge.entity.subscription import Subscription


class Unsubscribe:

    def __init__(self, db, sub_srv, log):
        self._db = db
        self._sub_srv = sub_srv
        self._log = log

    def __call__(self, sub_id):
        self._log.info('Calling Unsubscribe')
        sub = self._sub_srv.get_subscription(sub_id)
        assert sub.state == Subscription.State.Active
        sub.state = Subscription.State.Inactive
        self._db.commit()
