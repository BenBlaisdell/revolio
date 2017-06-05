import boto3
import botocore.client
import revolio as rv
from cached_property import threaded_cached_property

import nudge.core.app
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

    @threaded_cached_property
    def flask_config(self):
        return self._flask_config

    @threaded_cached_property
    def db_uri(self):
        return 'postgresql://{u}:{p}@{e}:5432/{db}'.format(
            e=self.config['Database']['Endpoint'],
            db=self.config['Database']['Name'],
            u=self.config['Database']['Username'],
            p=self.config['Database']['Password'],
        )

    @threaded_cached_property
    def ctx(self):
        return self

    @threaded_cached_property
    def config_s3_uri(self):
        return self._config_s3_uri

    @threaded_cached_property
    def def_queue_url(self):
        return self.config['Worker']['Deferral']['Env']['QueueUrl']

    # inject

    db = rv.Inject(nudge.core.db.Database)
    app = rv.Inject(nudge.core.app.App)
    config = rv.Inject(nudge.core.config.ConfigService)

    sub_srv = rv.Inject(nudge.core.entity.SubscriptionService)
    elem_srv = rv.Inject(nudge.core.entity.ElementService)
    batch_srv = rv.Inject(nudge.core.entity.BatchService)

    log = rv.Inject(nudge.core.log.LogService)
    deferral = rv.Inject(nudge.core.deferral.DeferralSrv)

    # functions

    attach_trigger = rv.Inject(nudge.core.function.AttachTrigger)
    backfill = rv.Inject(nudge.core.function.Backfill)
    consume = rv.Inject(nudge.core.function.Consume)
    get_active_batch = rv.Inject(nudge.core.function.GetActiveBatch)
    get_batch_elems = rv.Inject(nudge.core.function.GetBatchElements)
    get_sub_batches = rv.Inject(nudge.core.function.GetSubscriptionBatches)
    handle_object_created = rv.Inject(nudge.core.function.HandleObjectCreated)
    subscribe = rv.Inject(nudge.core.function.Subscribe)
    unsubscribe = rv.Inject(nudge.core.function.Unsubscribe)

    # aws

    @threaded_cached_property
    def sqs(self):
        # https://sqs.{region}.amazonaws.com/{account_id}/{name}
        region = self.config['Worker']['Deferral']['Env']['QueueUrl'].split('.', 2)[1]
        return boto3.client(
            service_name='sqs',
            region_name=region,
        )

    @threaded_cached_property
    def sns(self):
        return boto3.client('sns')

    @threaded_cached_property
    def s3(self):
        return boto3.client(
            service_name='s3',
            config=botocore.client.Config(signature_version='s3v4'),
        )
