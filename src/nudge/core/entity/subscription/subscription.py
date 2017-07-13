import enum
import uuid

import sqlalchemy as sa

import revolio as rv
import revolio.serializable
import revolio.sqlalchemy.types

from nudge.core.entity import Entity
from nudge.core.entity.subscription.trigger import SubscriptionTrigger


class SubscriptionState(enum.Enum):
    BACKFILLING = 'BACKFILLING'
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'


class Subscription(Entity):
    __tablename__ = 'subscription'

    id = sa.Column(
        sa.String,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
        primary_key=True,
    )

    State = SubscriptionState
    state = sa.Column(
        sa.Enum(State),
        default=State.ACTIVE,
        nullable=False,
    )

    bucket = sa.Column(
        sa.String,
        nullable=False,
    )

    prefix = sa.Column(
        sa.String,
        nullable=True
    )

    regex = sa.Column(
        revolio.sqlalchemy.types.Regex,
        nullable=True,
    )

    Trigger = SubscriptionTrigger
    trigger = sa.Column(
        rv.sqlalchemy.types.serializable(SubscriptionTrigger),
        nullable=True,
    )

    iris_id = sa.Column(
        sa.String,
    )

    def __repr__(self):
        return super().__repr__(id=self.id)
