import sqlalchemy as sa

from nudge.db import db, SubscriptionOrm, ElementOrm
from nudge.entity.element import Element
from nudge.entity.subscription import Subscription


def handle_obj_created(bucket, key, size, time):
    for sub in _get_matching_subs(bucket, key):
        _create_element(sub.id, bucket, key, size, time)
        elems = _get_sub_elems(sub.id)
        if _batch_size(elems) >= sub.threshold:
            _ping_endpoint(sub, elems)


def _get_matching_subs(bucket, key):
    return [
        Subscription.from_orm(sub_orm)
        for sub_orm in _get_matching_sub_orms(bucket, key)
    ]


def _get_matching_sub_orms(bucket, key):
    return SubscriptionOrm.query \
        .filter(SubscriptionOrm.bucket == bucket) \
        .filter(sa.sql.expression.bindparam('k', key).startswith(SubscriptionOrm.prefix)) \
        .all()


def _create_element(sub_id, bucket, key, size, time):
    elem = Element.create(
        subscription_id=sub_id,
        bucket=bucket,
        key=key,
        size=size,
        time=time,
    )

    db.session.add(elem.to_orm())
    db.session.flush()


def _get_sub_elems(sub_id):
    return [
        Element.from_orm(elem_orm)
        for elem_orm in _get_sub_elem_orms(sub_id)
    ]


def _get_sub_elem_orms(sub_id):
    return ElementOrm.query \
        .filter(ElementOrm.subscription_id == sub_id) \
        .all()


def _batch_size(elems):
    return sum(map(lambda e: e.size, elems))


def _ping_endpoint(sub, elems):
    sub.endpoint.send_message({
        'SubscriptionId': sub.id,
        'ElementIds': map(lambda e: e.id, elems),
    })
