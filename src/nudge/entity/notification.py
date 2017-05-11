import uuid

import sqlalchemy as sa
import sqlalchemy.orm.exc

from nudge.entity.entity import Entity
from nudge.orm import NotificationOrm


class NotificationService:

    def __init__(self, db):
        super(NotificationService, self).__init__()
        self._db = db

    def get_covered_notifications(self, n):
        return map(Notification.from_orm, self._get_covered_notifications(n))

    def _get_covered_notifications(self, n):
        return self._db \
            .query(NotificationOrm) \
            .filter(NotificationOrm.bucket == n.bucket) \
            .filter(NotificationOrm.prefix.startswith(sa.sql.expression.bindparam('p', n.prefix))) \
            .all()

    def get_covering_notification(self, n):
        covering = self._get_covering_notification(n)
        return Notification.to_orm(covering) if covering is not None else None

    def _get_covering_notification(self, n):
        try:
            self._db \
                .query(NotificationOrm) \
                .filter(NotificationOrm.bucket == n.bucket) \
                .filter(sa.sql.expression.bindparam('p', n.prefix).startswith(NotificationOrm.prefix)) \
                .one_or_none()
        except sa.orm.exc.MultipleResultsFound:
            raise Exception('Found overlapping notifications covering {}'.format(n))


class Notification(Entity):

    @property
    def bucket(self):
        return self._bucket

    @property
    def prefix(self):
        return self._prefix

    @property
    def c_id(self):
        return self._c_id

    @staticmethod
    def create(b, p):
        return Notification(
            bucket=b,
            prefix=p,
            c_id='nudge-subscription-{}'.format(str(uuid.uuid4())),
        )

    def to_orm(self):
        return NotificationOrm(
            bucket=self.bucket,
            prefix=self.prefix,
            c_id=self.c_id,
        )

    @staticmethod
    def from_orm(orm):
        return Notification(
            bucket=orm.bucket,
            prefix=orm.prefix,
            c_id=orm.c_id,
        )

    def __init__(self, bucket, prefix, c_id):
        super(Notification, self).__init__()
        self._bucket = bucket
        self._prefix = prefix
        self._c_id = c_id
