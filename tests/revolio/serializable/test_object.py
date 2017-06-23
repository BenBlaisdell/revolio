import enum

import pytest

import revolio as rv


_foo_bar_val_nested = 'foo_bar_nested_value'
_foo_baz_val = 2
_foo_bar_val = 'foo_bar_value'


class Fruit(rv.serializable.Serializable):
    ripe = rv.serializable.fields.Bool()


class Bananna(Fruit):
    length = rv.serializable.fields.Int()


class Apple(Fruit):

    class AppleType(enum.Enum):
        MACINTOSH = 'Macintosh'
        GRANNY_SMITH = 'Granny Smith'

    diameter = rv.serializable.fields.Int()
    type = rv.serializable.fields.Enum(AppleType)


class FruitType(enum.Enum):
    BANANNA = Bananna
    APPLE = Apple


class DummySerializable(rv.Serializable):
    fruit = rv.serializable.fields.ObjectEnum(FruitType)


def test_object_enum_deserialize():
    apple_diam = 10

    a = DummySerializable.deserialize({
        'Fruit': {
            'Type': FruitType.APPLE.name,
            'Parameters': {
                'Ripe': True,
                'Diameter': apple_diam,
                'Type': Apple.AppleType.MACINTOSH.name,
            },
        },
    })

    assert isinstance(a.fruit, Apple)
    assert a.fruit.diameter == apple_diam
    assert a.fruit.type == Apple.AppleType.MACINTOSH

    bananna_length = 4

    b = DummySerializable.deserialize({
        'Fruit': {
            'Type': FruitType.BANANNA.name,
            'Parameters': {
                'Ripe': True,
                'Length': bananna_length,
            },
        },
    })

    assert isinstance(b.fruit, Bananna)
    assert b.fruit.length == bananna_length
