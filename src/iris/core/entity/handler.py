import enum

import sqlalchemy as sa
import sqlalchemy.orm

import revolio as rv
import revolio.entity

from iris.core.entity import Entity
from iris.core.entity.notification import Notification
from iris.core.entity.listener import Listener


class Handler(Entity):
    __tablename__ = 'handler'

    id = sa.Column(
        sa.String,
        default=rv.entity.gen_id,
        nullable=False,
        primary_key=True,
    )

    protocol = sa.Column(
        sa.String,
        nullable=False,
    )

    endpoint = sa.Column(
        sa.String,
        nullable=False,
    )

    # listeners = sa.orm.relationship(
    #     'Listeners',
    #     back_populates='handler',
    #     primaryjoin=lambda: sa.and_(
    #         Notification.id == Listener.id,
    #         Listener.state == Listener.State.ACTIVE,
    #     ),
    # )

    def __repr__(self):
        return super().__repr__(id=self.id)


class HandlerService:

    def __init__(self, db):
        super().__init__()
        self._db = db

    def get_notification_handlers(self, nfn):
        return self._db \
            .query(Handler) \
            .filter(Handler.id == Listener.handler_id) \
            .filter(Listener.state == Listener.State.ACTIVE) \
            .filter(Listener.notification_id == nfn.id) \
            .all()
