import click
import subprocess


class EnumType(click.Choice):

    def __init__(self, enum):
        super(EnumType, self).__init__(enum.__members__)
        self._enum = enum

    def convert(self, value, param, ctx):
        if isinstance(value, self._enum):
            return value

        return self._enum[super(EnumType, self).convert(value, param, ctx)]
