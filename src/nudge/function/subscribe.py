from nudge.entity.subscription import Subscription


class Subscribe:

    def __init__(self, db):
        self._db = db

    def __call__(self, bucket, endpoint, *, prefix=None, regex=None, threshold=0):
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
