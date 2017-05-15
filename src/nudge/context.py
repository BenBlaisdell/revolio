import boto3
import botocore.client
from werkzeug.utils import cached_property

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

    @cached_property
    def flask_config(self):
        return self._flask_config

    @cached_property
    def db_uri(self):
        return 'postgresql://{u}:{p}@{e}:5432/{db}'.format(
            e=self.config['Database']['Endpoint'],
            db=self.config['Database']['Name'],
            u=self.config['Database']['Username'],
            p=self.config['Database']['Password'],
        )

    @cached_property
    def ctx(self):
        return self

    @cached_property
    def config_s3_uri(self):
        return self._config_s3_uri

    # inject

    @cached_property
    def db(self):
        return nudge.db.Database(
            log=self.log,
            db_uri=self.db_uri,
        )

    @cached_property
    def app(self):
        return nudge.app.App(
            ctx=self,
            flask_config=self.flask_config,
            db=self.db,
        )

    @cached_property
    def config(self):
        return nudge.config.ConfigService(
            log=self.log,
            s3=self.s3,
            config_s3_uri=self.config_s3_uri,
        )

    @cached_property
    def sub_srv(self):
        return nudge.entity.subscription.SubscriptionService(
            db=self.db,
        )


    @cached_property
    def elem_srv(self):
        return nudge.entity.element.ElementService(
            db=self.db,
        )

    @cached_property
    def nfn_srv(self):
        return nudge.entity.notification.NotificationService(
            db=self.db,
        )

    @cached_property
    def batch_srv(self):
        return nudge.batch.BatchService(
            ctx=self,
            db=self.db,
        )

    @cached_property
    def log(self):
        return nudge.log.LogService()

    # functions

    @cached_property
    def subscribe(self):
        return nudge.function.subscribe.Subscribe(
            db=self.db,
        )

    @cached_property
    def handle_obj_created(self):
        return nudge.function.handle_obj_created.HandleObjectCreated(
            db=self.db,
            sub_srv=self.sub_srv,
            batch_srv=self.batch_srv,
            elem_srv=self.elem_srv,
        )

    @cached_property
    def consume(self):
        return nudge.function.consume.Consume(
            log=self.log,
            elem_srv=self.elem_srv,
            db=self.db,
        )

    @cached_property
    def unsubscribe(self):
        return nudge.function.unsubscribe.Unsubscribe(
            db=self.db,
            sub_srv=self.sub_srv,
        )

    # aws

    @cached_property
    def sqs(self):
        return boto3.client('sqs')

    @cached_property
    def sns(self):
        return boto3.client('sns')

    @cached_property
    def s3(self):
        return boto3.client(
            service_name='s3',
            config=botocore.client.Config(signature_version='s3v4'),
        )
