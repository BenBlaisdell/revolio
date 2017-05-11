import abc

from nudge.orm import EntityOrm


class Entity(metaclass=abc.ABCMeta):

    def __init__(self):
        super(Entity, self).__init__()

    @abc.abstractmethod
    def to_orm(self):
        return EntityOrm()

    @staticmethod
    @abc.abstractmethod
    def from_orm(orm):
        return Entity()

    @abc.abstractmethod
    def create(self, *args, **kwargs):
        return Entity()


