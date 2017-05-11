import sqlalchemy as sa
import sqlalchemy.dialects.postgresql
import sqlalchemy.ext.declarative


class EntityOrmMixin:

    created = sa.Column(
        sa.TIMESTAMP,
        server_default=sa.sql.expression.func.current_timestamp(),
    )

    updated = sa.Column(
        sa.TIMESTAMP,
        server_default=sa.sql.expression.func.current_timestamp(),
        onupdate=sa.sql.expression.func.current_timestamp(),
    )

    data = sa.Column(sa.dialects.postgresql.JSONB)


EntityOrm = sa.ext.declarative.declarative_base(cls=EntityOrmMixin)


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
    c_id = sa.Column(sa.String)


class ElementOrm(EntityOrm):
    __tablename__ = 'element'

    id = sa.Column(sa.String, primary_key=True)
    state = sa.Column(sa.String)
    bucket = sa.Column(sa.String)
    key = sa.Column(sa.String)
    subscription = sa.Column(sa.String)
