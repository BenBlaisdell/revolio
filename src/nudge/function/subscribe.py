from nudge.entity.subscription import Subscription


class Subscribe:

    def __init__(self, db, log):
        self._db = db
        self._log = log

    def __call__(self, bucket, endpoint, *, prefix=None, regex=None, threshold=0):
        self._log.info('Calling Subscribe')
        sub = Subscription.create(
            bucket=bucket,
            endpoint=endpoint,
            prefix=prefix,
            regex=regex,
            threshold=threshold,
        )

        self._db.add(sub)
        self._db.commit()

        return sub
