import enum

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql
import sqlalchemy.ext.mutable
import sqlalchemy.orm.exc

import revolio as rv
import revolio.entity

from iris.core.entity import Entity
from iris.core.entity.listener import Listener


class NotificationState(enum.Enum):
    ACTIVE = 'ACTIVE'
    CONSOLIDATED = 'CONSOLIDATED'
    DEACTIVATED = 'DEACTIVATED'


class Notification(Entity):
    __tablename__ = 'notification'

    id = sa.Column(
        sa.String,
        default=rv.entity.gen_id,
        nullable=False,
        primary_key=True,
    )

    State = NotificationState

    state = sa.Column(
        sa.Enum(NotificationState),
        nullable=False,
    )

    bucket = sa.Column(
        sa.String,
        nullable=False,
    )

    prefix = sa.Column(
        sa.String,
        nullable=True,
    )

    topic_config_id = sa.Column(
        sa.String,
        nullable=False,
    )

    topic_arn = sa.Column(
        sa.String,
        nullable=False,
    )

    topic_subscriptions = sa.Column(
        sa.ext.mutable.MutableDict.as_mutable(sa.dialects.postgresql.JSONB),
        default=dict,
    )

    listeners = sa.orm.relationship(
        'Listener',
        primaryjoin=lambda: sa.and_(
            Notification.id == Listener.notification_id,
            Listener.state == Listener.State.ACTIVE,
        ),
    )

    direct_listeners = sa.orm.relationship(
        'Listener',
        primaryjoin=lambda: sa.and_(
            Notification.id == Listener.notification_id,
            Listener.state == Listener.State.ACTIVE,
            Notification.prefix == Listener.prefix,
        ),
    )

    def __repr__(self):
        return super().__repr__(id=self.id)

    @property
    def topic_notification_config(self):
        c = {
            'Id': self.topic_config_id,
            'TopicArn': self.topic_arn,
            'Events': ['s3:ObjectCreated:*'],
        }

        if self.prefix is not None:
            c['Filter'] = {
                'Key': {
                    'FilterRules': [{
                        'Name': 'prefix',
                        'Value': self.prefix,
                    }],
                },
            }

        return c


class NotificationService:

    def __init__(self, db):
        super().__init__()
        self._db = db

    def get_covering_notification(self, bucket, prefix):
        try:
            return self._db \
                .query(Notification) \
                .filter(Notification.state == Notification.State.ACTIVE) \
                .filter(Notification.bucket == bucket) \
                .filter(sa.or_(
                    sa.sql.expression.bindparam('p', prefix).startswith(Notification.prefix),
                    Notification.prefix == None,
                )) \
                .one_or_none()
        except sa.orm.exc.MultipleResultsFound:
            raise Exception(f'Found overlapping active notifications covering s3://{bucket}/{prefix}')

    def get_covered_notifications(self, bucket, prefix):
        return self._db \
            .query(Notification) \
            .filter(Notification.state == Notification.State.ACTIVE) \
            .filter(Notification.bucket == bucket) \
            .filter(Notification.prefix.startswith(sa.sql.expression.bindparam('p', prefix))) \
            .all()
