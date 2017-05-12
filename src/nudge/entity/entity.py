import abc

from nudge.orm import EntityOrm


class Entity:

    def __init__(self, orm):
        super(Entity, self).__init__()
        self._orm = orm

    @abc.abstractmethod
    def create(self, *args, **kwargs):
        return Entity(EntityOrm(*args, **kwargs))

    @property
    def orm(self):
        return self._orm
