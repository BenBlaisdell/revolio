import click
import subprocess


class EnumType(click.Choice):

    def __init__(self, enum):
        super(EnumType, self).__init__(enum.__members__)
        self._enum = enum

    def convert(self, value, param, ctx):
        return self._enum[super(EnumType, self).convert(value, param, ctx)]


