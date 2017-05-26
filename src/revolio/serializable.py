import abc


class Serializable(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def serialize(self):
        pass

    @staticmethod
    @abc.abstractmethod
    def deserialize(*args, **kwargs):
        pass
