from nudge.db import db
from nudge.entity.subscription import Subscription


def subscribe(bucket, endpoint, *, prefix=None, regex=None, threshold=0):
    sub = Subscription.create(
        bucket=bucket,
        endpoint=endpoint,
        prefix=prefix,
        regex=regex,
        threshold=threshold,
    )

    db.add(sub.to_orm())
    db.commit()
    return sub
