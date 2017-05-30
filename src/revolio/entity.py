import abc


class Entity(metaclass=abc.ABCMeta):

    def __init__(self, orm):
        super(Entity, self).__init__()
        self._orm = orm

    @staticmethod
    @abc.abstractmethod
    def create(*args, **kwargs):
        pass  # return Entity(EntityOrm(*args, **kwargs))

    @property
    def orm(self):
        return self._orm
