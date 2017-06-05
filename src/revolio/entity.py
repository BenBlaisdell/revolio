import abc
import datetime as dt


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
            attrs=', '.join('{}={}'.format(k, v) for k, v in kwargs.items()),
        )

    def __repr__(self):
        return str(self)
