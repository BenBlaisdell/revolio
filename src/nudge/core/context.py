import boto3
import botocore.client
from werkzeug.utils import cached_property

import nudge.core.app
import nudge.core.batch
import nudge.core.config
import nudge.core.db
import nudge.core.deferral
import nudge.core.entity
import nudge.core.function
import nudge.core.log


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
        return nudge.core.db.Database(
            log=self.log,
            db_uri=self.db_uri,
        )

    @cached_property
    def app(self):
        return nudge.core.app.App(
            ctx=self,
            flask_config=self.flask_config,
            db=self.db,
            log=self.log,
        )

    @cached_property
    def config(self):
        return nudge.core.config.ConfigService(
            log=self.log,
            s3=self.s3,
            config_s3_uri=self.config_s3_uri,
        )

    @cached_property
    def sub_srv(self):
        return nudge.core.entity.SubscriptionService(
            db=self.db,
        )

    @cached_property
    def elem_srv(self):
        return nudge.core.entity.ElementService(
            db=self.db,
        )

    @cached_property
    def nfn_srv(self):
        return nudge.core.entity.NotificationService(
            db=self.db,
        )

    @cached_property
    def batch_srv(self):
        return nudge.core.batch.BatchService(
            ctx=self,
            db=self.db,
        )

    @cached_property
    def log(self):
        return nudge.core.log.LogService()

    @cached_property
    def deferral(self):
        return nudge.core.deferral.DeferralSrv(
            app=self.app,
            sqs=self.sqs,
            queue_url=self.config['DeferralQueueUrl'],
        )

    # functions

    @cached_property
    def subscribe(self):
        return nudge.core.function.Subscribe(
            db=self.db,
            log=self.log,
        )

    @cached_property
    def backfill(self):
        return nudge.core.function.Backfill(
            db=self.db,
            log=self.log,
            sub_srv=self.sub_srv,
            s3=self.s3,
            deferral=self.deferral,
        )

    @cached_property
    def handle_object_created(self):
        return nudge.core.function.HandleObjectCreated(
            db=self.db,
            sub_srv=self.sub_srv,
            batch_srv=self.batch_srv,
            elem_srv=self.elem_srv,
            log=self.log,
        )

    @cached_property
    def get_batch(self):
        return nudge.core.function.get_batch.GetBatch(
            elem_srv=self.elem_srv,
            log=self.log,
        )

    @cached_property
    def consume(self):
        return nudge.core.function.Consume(
            log=self.log,
            elem_srv=self.elem_srv,
            db=self.db,
        )

    @cached_property
    def unsubscribe(self):
        return nudge.core.function.Unsubscribe(
            db=self.db,
            sub_srv=self.sub_srv,
            log=self.log,
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
