import abc
import datetime as dt
import uuid

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql
import sqlalchemy.ext.declarative
import sqlalchemy.ext.mutable


DUMMY_ID = '00000000-1111-2222-3333-444444444444'


def gen_id():
    return str(uuid.uuid4())


class MutableDict(sa.ext.mutable.Mutable, dict):
    @classmethod
    def coerce(cls, key, value):
        "Convert plain dictionaries to MutableDict."

        if not isinstance(value, MutableDict):
            if isinstance(value, dict):
                return MutableDict(value)

            # this call will raise ValueError
            return sqlalchemy.ext.mutable.Mutable.coerce(key, value)
        else:
            return value

    def __setitem__(self, key, value):
        "Detect dictionary set events and emit change events."

        dict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        "Detect dictionary del events and emit change events."

        dict.__delitem__(self, key)
        self.changed()


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

    data = sa.Column(
        sa.ext.mutable.MutableDict.as_mutable(sa.dialects.postgresql.JSONB),
        default=dict,
    )

    def __repr__(self, **kwargs):
        return '<{}>'.format(' '.join([
            type(self).__name__,
            *[f'{k}={v}' for k, v in kwargs.items()],
        ]))


def declarative_base():
    return sa.ext.declarative.declarative_base(cls=EntityOrmMixin)


class Entity(metaclass=abc.ABCMeta):

    def __init__(self, orm):
        super(Entity, self).__init__()
        self._orm = orm

    @property
    def created(self):
        return dt.datetime.strptime(self._orm.created, '%Y-%m-%d %H:%M:%S')

    @property
    def updated(self):
        return dt.datetime.strptime(self._orm.updated, '%Y-%m-%d %H:%M:%S')

    @staticmethod
    @abc.abstractmethod
    def create(*args, **kwargs):
        pass  # return Entity(EntityOrm(*args, **kwargs))

    @property
    def orm(self):
        return self._orm

    def __str__(self, **kwargs):
        return '{type}<{attrs}>'.format(
            type=type(self).__name__,
            attrs=', '.join(f'{k}={v}' for k, v in kwargs.items()),
        )

    def __repr__(self):
        return str(self)
