import pytest

import revolio as rv


_foo_bar_val_nested = 'foo_bar_nested_value'
_foo_baz_val = 2
_foo_bar_val = 'foo_bar_value'


class NestedSerializable(rv.Serializable):

    foo_bar = rv.serializable.fields.Str()
    foo_baz = rv.serializable.fields.Int()


class BaseSerializable(rv.Serializable):

    foo_bar = rv.serializable.fields.Str()
    nested = rv.serializable.fields.Nested(NestedSerializable)


def test_nested_deserialize():
    s = BaseSerializable.deserialize({
        'FooBar': _foo_bar_val,
        'Nested': {
            'FooBar': _foo_bar_val_nested,
            'FooBaz': _foo_baz_val,
        },
    })

    assert isinstance(s, BaseSerializable)
    assert s.foo_bar == _foo_bar_val
    assert isinstance(s.nested, NestedSerializable)
    assert s.nested.foo_bar == _foo_bar_val_nested
    assert s.nested.foo_baz == _foo_baz_val


def test_nested_deserialize_invalid():
    with pytest.raises(Exception):
        s = BaseSerializable.deserialize({
            'FooBar': 3,
            'Nested': {
                'FooBar': _foo_bar_val_nested,
                'FooBaz': _foo_baz_val,
            },
        })

        print(s)


    with pytest.raises(Exception):
        BaseSerializable.deserialize({
            'FooBar': 3,
            'Nested': {
                'FooBar': _foo_bar_val_nested,
                'FooBaz': 'invalid_format_value',
            },
        })


def test_nested_programmatic():
    s = BaseSerializable(
        foo_bar=_foo_bar_val,
        nested=NestedSerializable(
            foo_bar=_foo_bar_val_nested,
            foo_baz=_foo_baz_val,
        ),
    )

    assert isinstance(s, BaseSerializable)
    assert s.foo_bar == _foo_bar_val
    assert isinstance(s.nested, NestedSerializable)
    assert s.nested.foo_bar == _foo_bar_val_nested
    assert s.nested.foo_baz == _foo_baz_val


def test_nested_programmatic_invalid():
    with pytest.raises(Exception):
        BaseSerializable(
            foo_bar=_foo_bar_val,
            nested=NestedSerializable(
                foo_bar=_foo_bar_val_nested,
                foo_baz='invalid_format_value',
            ),
        )

    with pytest.raises(Exception):
        BaseSerializable(
            foo_bar=3,
            nested=NestedSerializable(
                foo_bar=_foo_bar_val_nested,
                foo_baz=_foo_baz_val,
            ),
        )