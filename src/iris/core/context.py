import logging

import boto3
from cached_property import cached_property

import revolio as rv
import revolio.inject
import revolio.config
import revolio.db
import revolio.logging

import iris
import iris.core.app
import iris.core.entity
import iris.core.function
import iris.core.sns
import iris.core.sqs
import iris.core.s3
import iris.core.watch


class IrisConfigService(rv.config.ConfigService):
    ENV_VAR_PREFIX = 'IRS_APP'


class IrisContext:

    def __init__(self, *, flask_config=None, sqlalchemy_level=logging.DEBUG):
        rv.logging.init_flask(iris, sqlalchemy_level=sqlalchemy_level)
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

    entity = iris.core.entity.Entity

    # inject

    db = rv.inject.Inject(rv.db.Database)
    app = rv.inject.Inject(iris.core.app.App)
    config = rv.inject.Inject(IrisConfigService)

    watcher = rv.inject.Inject(iris.core.watch.WatchService)
    s3 = rv.inject.Inject(iris.core.s3.S3)
    sqs = rv.inject.Inject(iris.core.sqs.Sqs)
    sns = rv.inject.Inject(iris.core.sns.Sns)

    # entities

    nfn_srv = rv.inject.Inject(iris.core.entity.NotificationService)
    lst_srv = rv.inject.Inject(iris.core.entity.ListenerService)
    hlr_srv = rv.inject.Inject(iris.core.entity.HandlerService)

    # functions

    add_listener = rv.inject.Inject(iris.core.function.AddListener)
    remove_listener = rv.inject.Inject(iris.core.function.RemoveListener)
