import boto3
from cached_property import cached_property

import nudge.app
import nudge.db
from nudge.batch import BatchService
from nudge.entity.notification import NotificationService
from nudge.entity.subscription import SubscriptionService
from nudge.function import FunctionDirectory


class ElementService:

    def __init__(self, session):
        self._session = session


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
    def functions(self):
        return FunctionDirectory(
            ctx=self,
        )

    @property
    def sub_srv(self):
        return SubscriptionService(
            session=self.db.session,
        )

    @property
    def elem_srv(self):
        return ElementService(
            session=self.db.session,
        )

    @property
    def nfn_srv(self):
        return NotificationService(
            session=self.db.session,
        )

    @property
    def batch_srv(self):
        return BatchService(
            ctx=self,
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
        return boto3.client('s3')
