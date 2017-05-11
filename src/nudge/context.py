import boto3
from cached_property import cached_property

import revolio as rv

import nudge.app
import nudge.db
import nudge.batch
import nudge.entity.notification
import nudge.entity.subscription
import nudge.entity.element
import nudge.function
import nudge.function.consume
import nudge.function.handle_obj_created
import nudge.function.subscribe
import nudge.function.unsubscribe


class NudgeContext:

    def __init__(self, db_uri, *, app_configs=None):
        self._app = nudge.app.create_app(
            ctx=self,
            configs=(app_configs or {}),
        )

        self._db = nudge.db.create_db(
            app=self._app,
            uri=db_uri,
        )

    def run(self):
        self._app.run()

    @property
    def app(self):
        return self._app

    @property
    def db(self):
        return self._db

    @property
    def session(self):
        return self.db.session

    @property
    def engine(self):
        return self.db.engine

    @property
    def ctx(self):
        return self

    # inject

    sub_srv = rv.Inject(nudge.entity.subscription.SubscriptionService)

    elem_srv = rv.Inject(nudge.entity.element.ElementService)

    nfn_srv = rv.Inject(nudge.entity.notification.NotificationService)

    batch_srv = rv.Inject(nudge.batch.BatchService)

    # functions

    subscribe = rv.Inject(nudge.function.subscribe.Subscribe)

    handle_obj_created = rv.Inject(nudge.function.handle_obj_created.HandleObjectCreated)

    consume = rv.Inject(nudge.function.consume.Consume)

    unsubscribe = rv.Inject(nudge.function.unsubscribe.Unsubscribe)

    # aws

    @cached_property
    def sqs(self):
        return boto3.client('sqs')

    @cached_property
    def sns(self):
        return boto3.client('sns')

    @cached_property
    def s3(self):
        return boto3.client('s3')
