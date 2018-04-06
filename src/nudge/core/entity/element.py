import datetime as dt
import enum
import logging
import uuid

import revolio as rv
import sqlalchemy as sa

from nudge.core.entity import Entity


_log = logging.getLogger(__name__)


class ElementState(enum.Enum):
    AVAILABLE = 'AVAILABLE'
    BATCHED = 'BATCHED'


class Element(Entity):
    __tablename__ = 'element'

    id = sa.Column(
        sa.String,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
        primary_key=True,
    )

    State = ElementState
    state = sa.Column(
        sa.Enum(State),
        default=State.AVAILABLE,
        nullable=False,
    )

    # todo: map to other tables
    sub_id = sa.Column(
        sa.String,
        nullable=False,
    )

    # todo: map to other tables
    batch_id = sa.Column(
        sa.String,
        nullable=True,
    )

    bucket = sa.Column(
        sa.String,
        nullable=False,
    )

    key = sa.Column(
        sa.String,
        nullable=False,
    )

    size = sa.Column(
        sa.Integer,
        nullable=False,
    )

    s3_created = sa.Column(
        sa.DateTime,
        nullable=False,
    )

    def __repr__(self):
        return super().__repr__(id=self.id)


# service


class ElementService:

    def __init__(self, db):
        self._db = db

    def get_elements(self, elem_ids):
        elems = self._db \
            .query(Element) \
            .filter(Element.id.in_(elem_ids)) \
            .all()

        elems = list(elems)
        assert len(elems) == len(elem_ids)
        _log.debug(f'Found elements by id: {elems}')
        return elems

    def get_batchable_sub_elems(self, sub_id, *, limit=4096):
        """Get the oldest available elements for a subscription by s3_created time."""
        elems = self.get_sub_elems(
            sub_id=sub_id,
            state=Element.State.AVAILABLE,
            order_by=Element.s3_created.asc(),
            limit=limit,
        )

        _log.debug(f'Found batchable elements for subscription {sub_id}: {elems}')
        return elems

    def get_sub_elems(self, sub_id, state, *, order_by=None, limit=None, offset=0):
        """Get elements for a subscription.

        :type sub_id: str
        :type state: nudge.core.entity.element.ElementState
        :type order_by:
        :type limit: int
        :type offset: int
        """
        elems = self._db \
            .query(Element) \
            .filter(Element.sub_id == sub_id) \
            .filter(Element.state == state.value) \
            .order_by(order_by) \
            .limit(limit) \
            .offset(offset) \
            .all()

        return list(elems)

    def get_batch_elems(self, sub_id, batch_id, *, offset=0, limit=None):
        elems = self._db \
            .query(Element) \
            .filter(Element.sub_id == sub_id) \
            .filter(Element.state == Element.State.BATCHED.value) \
            .filter(Element.batch_id == batch_id) \
            .limit(limit) \
            .offset(offset) \
            .all()

        elems = list(elems)
        _log.debug(f'Found elements for batch {batch_id}: {elems}')
        return elems
