import abc


class Serializable(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def serialize(self):
        return {}

    @staticmethod
    @abc.abstractmethod
    def deserialize(data):
        return Serializable()
