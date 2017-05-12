from nudge.entity.subscription import Subscription


class Subscribe:

    def __init__(self, session):
        self._session = session

    def __call__(self, bucket, endpoint, *, prefix=None, regex=None, threshold=0):
        sub = Subscription.create(
            bucket=bucket,
            endpoint=endpoint,
            prefix=prefix,
            regex=regex,
            threshold=threshold,
        )

        self._session.add(sub.orm)
        self._session.commit()

        return sub
