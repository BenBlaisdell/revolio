import boto3
from cached_property import cached_property

import revolio as rv

import nudge.app
import nudge.batch
import nudge.config
import nudge.db
import nudge.entity.element
import nudge.entity.notification
import nudge.entity.subscription
import nudge.function
import nudge.function.consume
import nudge.function.handle_obj_created
import nudge.function.subscribe
import nudge.function.unsubscribe
import nudge.log


class NudgeContext:

    def __init__(self, config_s3_uri, *, flask_config=None):
        self._config_s3_uri = config_s3_uri
        self._flask_config = flask_config or {}

        self.db.init(self.app.flask_app)

    @property
    def flask_config(self):
        return self._flask_config

    @property
    def db_uri(self):
        return 'postgresql://{u}:{p}@{e}:5432/{db}'.format(
            e=self.config['Database']['Endpoint'],
            db=self.config['Database']['Name'],
            u=self.config['Database']['Username'],
            p=self.config['Database']['Password'],
        )

    @property
    def ctx(self):
        return self

    @property
    def config_s3_uri(self):
        return self._config_s3_uri

    # inject

    config = rv.Inject(nudge.config.ConfigService)

    db = rv.Inject(nudge.db.Database)

    app = rv.Inject(nudge.app.App)

    sub_srv = rv.Inject(nudge.entity.subscription.SubscriptionService)

    elem_srv = rv.Inject(nudge.entity.element.ElementService)

    nfn_srv = rv.Inject(nudge.entity.notification.NotificationService)

    batch_srv = rv.Inject(nudge.batch.BatchService)

    log = rv.Inject(nudge.log.LogService)

    # functions

    subscribe = rv.Inject(nudge.function.subscribe.Subscribe)

    handle_obj_created = rv.Inject(nudge.function.handle_obj_created.HandleObjectCreated)

    consume = rv.Inject(nudge.function.consume.Consume)

    unsubscribe = rv.Inject(nudge.function.unsubscribe.Unsubscribe)


    # db

    def recreate_tables(self):
        raise NotImplementedError()

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
