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


def declarative_base():
    return sa.ext.declarative.declarative_base(cls=EntityOrmMixin)
