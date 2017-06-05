import sqlalchemy as sa

import revolio as rv


EntityOrm = rv.declarative_base()


class SubscriptionOrm(EntityOrm):
    __tablename__ = 'subscription'

    id = sa.Column(sa.String, primary_key=True)
    state = sa.Column(sa.String)
    bucket = sa.Column(sa.String)
    prefix = sa.Column(sa.String)


class NotificationOrm(EntityOrm):
    __tablename__ = 'notification'

    bucket = sa.Column(sa.String, primary_key=True)
    prefix = sa.Column(sa.String, primary_key=True)
    config_id = sa.Column(sa.String)


class ElementOrm(EntityOrm):
    __tablename__ = 'element'

    id = sa.Column(sa.String, primary_key=True)
    state = sa.Column(sa.String)
    sub_id = sa.Column(sa.String)
    batch_id = sa.Column(sa.String)


class BatchOrm(EntityOrm):
    __tablename__ = 'batch'

    id = sa.Column(sa.String, primary_key=True)
    state = sa.Column(sa.String)
    sub_id = sa.Column(sa.String)
