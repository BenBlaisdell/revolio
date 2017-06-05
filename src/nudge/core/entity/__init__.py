import revolio as rv


EntityOrm = rv.declarative_base()


from nudge.core.entity.subscription import (
    Subscription,
    SubscriptionOrm,
    SubscriptionService,
)


from nudge.core.entity.element import (
    Element,
    ElementOrm,
    ElementService,
)


from nudge.core.entity.batch import (
    Batch,
    BatchOrm,
    BatchService,
)


# from nudge.core.entity.notification import (
#     Notification,
#     NotificationOrm,
#     NotificationService,
# )
