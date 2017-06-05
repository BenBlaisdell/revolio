import uuid

import revolio as rv
import sqlalchemy as sa
import sqlalchemy.orm.exc

from nudge.core.entity import EntityOrm


# intended to track s3 object creation notifications
# not currently in use


class Notification(rv.Entity):

    @property
    def bucket(self):
        return self._orm.bucket

    @property
    def prefix(self):
        return self._orm.prefix

    @property
    def config_id(self):
        return self._orm.config_id

    @staticmethod
    def create(bucket, prefix):
        return Notification(NotificationOrm(
            bucket=bucket,
            prefix=prefix,
            config_id='nudge-notification-{}'.format(str(uuid.uuid4())),
        ))


# orm


class NotificationOrm(EntityOrm):
    __tablename__ = 'notification'

    bucket = sa.Column(sa.String, primary_key=True)
    prefix = sa.Column(sa.String, primary_key=True)
    config_id = sa.Column(sa.String)


# service


class NotificationService:

    def __init__(self, db):
        super(NotificationService, self).__init__()
        self._db = db

    def get_covered_notifications(self, nfn):
        return [
            Notification(orm)
            for orm in self._db
                .query(NotificationOrm)
                .filter(NotificationOrm.bucket == nfn.bucket)
                .filter(NotificationOrm.prefix.startswith(sa.sql.expression.bindparam('p', nfn.prefix)))
                .all()
        ]

    def get_covering_notification(self, nfn):
        try:
            orm = self._db \
                .query(NotificationOrm) \
                .filter(NotificationOrm.bucket == nfn.bucket) \
                .filter(sa.sql.expression.bindparam('p', nfn.prefix).startswith(NotificationOrm.prefix)) \
                .one_or_none()
        except sa.orm.exc.MultipleResultsFound:
            raise Exception('Found overlapping notifications covering {}'.format(nfn))

        return Notification(orm) if (orm is not None) else None
