import boto3
import botocore.client
from cached_property import cached_property

import revolio as rv
import revolio.inject
import revolio.config
import revolio.db
import revolio.logging

import nudge
import nudge.core.app
import nudge.core.deferral
import nudge.core.entity
import nudge.core.function
import nudge.core.iris
import nudge.core.ping


class NudgeConfigService(rv.config.ConfigService):
    ENV_VAR_PREFIX = 'NDG_APP'


class NudgeCoreContext:

    def __init__(self, *, flask_config=None):
        rv.logging.init_flask(nudge)
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
    def def_queue_url(self):
        return self.config['Worker']['Deferral']['Env']['QueueUrl']

    entity = nudge.core.entity.Entity

    # inject

    db = rv.inject.Inject(rv.db.Database)
    app = rv.inject.Inject(nudge.core.app.App)
    config = rv.inject.Inject(NudgeConfigService)

    deferral = rv.inject.Inject(nudge.core.deferral.DeferralSrv)
    ping_srv = rv.inject.Inject(nudge.core.ping.PingService)

    iris = rv.inject.Inject(nudge.core.iris.IrisClient)

    # entities

    sub_srv = rv.inject.Inject(nudge.core.entity.SubscriptionService)
    elem_srv = rv.inject.Inject(nudge.core.entity.ElementService)
    batch_srv = rv.inject.Inject(nudge.core.entity.BatchService)

    # functions

    attach_trigger = rv.inject.Inject(nudge.core.function.AttachTrigger)
    backfill = rv.inject.Inject(nudge.core.function.Backfill)
    consume = rv.inject.Inject(nudge.core.function.Consume)
    create_batch = rv.inject.Inject(nudge.core.function.CreateBatch)
    get_batch_elems = rv.inject.Inject(nudge.core.function.GetBatchElements)
    get_sub_batches = rv.inject.Inject(nudge.core.function.GetSubscriptionBatches)
    get_subscription = rv.inject.Inject(nudge.core.function.GetSubscription)
    handle_object_created = rv.inject.Inject(nudge.core.function.HandleObjectCreated)
    subscribe = rv.inject.Inject(nudge.core.function.Subscribe)
    unsubscribe = rv.inject.Inject(nudge.core.function.Unsubscribe)

    # aws

    @cached_property
    def sqs(self):
        # https://sqs.{region}.amazonaws.com/{account_id}/{name}
        region = self.config['Worker']['Deferral']['Env']['QueueUrl'].split('.', 2)[1]
        return boto3.client(
            service_name='sqs',
            region_name=region,
        )

    @cached_property
    def sns(self):
        return boto3.client('sns')

    @cached_property
    def s3(self):
        return boto3.client(
            service_name='s3',
            config=botocore.client.Config(signature_version='s3v4'),
        )
