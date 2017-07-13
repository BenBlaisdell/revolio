import enum
import uuid

import sqlalchemy as sa
import sqlalchemy.orm

import revolio as rv
import revolio.serializable
import revolio.sqlalchemy.types

from iris.core.entity import Entity


class ListenerEndpoint(rv.serializable.Serializable):
    pass


class SqsEndpoint(ListenerEndpoint):
    queue_url = rv.serializable.fields.Str()


class ListenerEndpointProtocol(enum.Enum):
    SQS = SqsEndpoint


class ListenerState(enum.Enum):
    ACTIVE = 'ACTIVE'
    DEACTIVATED = 'DEACTIVATED'


class Listener(Entity):
    __tablename__ = 'listener'

    id = sa.Column(
        sa.String,
        default=lambda: str(uuid.uuid4()),
        primary_key=True,
    )

    State = ListenerState

    state = sa.Column(
        sa.Enum(State),
        nullable=False,
    )

    tag = sa.Column(
        sa.String,
        nullable=True,
    )

    bucket = sa.Column(
        sa.String,
        nullable=False,
    )

    prefix = sa.Column(
        sa.String,
        nullable=True,
    )

    notification_id = sa.Column(
        sa.String,
        sa.ForeignKey('notification.id'),
        nullable=False,
    )

    notification = sa.orm.relationship(
        'Notification',
    )

    handler_id = sa.Column(
        sa.String,
        sa.ForeignKey('handler.id'),
    )

    handler = sa.orm.relationship(
        'Handler',
    )

    def __repr__(self):
        return super().__repr__(id=self.id)


class ListenerService:

    def __init__(self, db):
        super().__init__()
        self._db = db

    def get_listener(self, id):
        return self._db \
            .query(Listener) \
            .get(id)

    def get_covered_listeners(self, bucket, prefix):
        query = self._db \
            .query(Listener) \
            .filter(Listener.state == Listener.State.ACTIVE) \
            .filter(Listener.bucket == bucket)

        if prefix is not None:
            query = query \
                .filter(Listener.prefix.startswith(sa.sql.expression.bindparam('p', prefix)))

        return query \
            .order_by(Listener.prefix) \
            .all()

    def exists_endpoint_listening(self, bucket, prefix, endpoint):
        query = self._db \
            .query(Listener) \
            .filter(Listener.state == Listener.State.ACTIVE) \
            .filter(Listener.bucket == bucket) \
            .filter(Listener.endpoint == endpoint)

        if prefix is not None:
            query = query \
                .filter(Listener.prefix.startswith(sa.sql.expression.bindparam('p', prefix)))

        return query \
            .exists()
