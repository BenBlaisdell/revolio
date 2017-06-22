import pytest
import revolio as rv


_foo_bar_val = 'foo_bar_value'
_foo_baz_val = 2


class SimpleSerializable(rv.Serializable):

    foo_bar = rv.serializable.fields.Str()
    foo_baz = rv.serializable.fields.Int()


def test_programatic():
    s = SimpleSerializable(
        foo_bar=_foo_bar_val,
        foo_baz=_foo_baz_val,
    )

    assert s.foo_bar == _foo_bar_val
    assert s.foo_baz == _foo_baz_val


def test_programmatic_invalid():
    with pytest.raises(Exception):
        SimpleSerializable(
            foo_bar=_foo_bar_val,
            foo_baz='invalid_type_value',
        )

    with pytest.raises(Exception):
        SimpleSerializable(
            foo_bar=3,
            foo_baz=_foo_baz_val,
        )


def test_deserialize():
    s = SimpleSerializable.deserialize({
        'FooBar': _foo_bar_val,
        'FooBaz': _foo_baz_val,
    })

    assert s.foo_bar == _foo_bar_val
    assert s.foo_baz == _foo_baz_val


def test_deserialize_invalid():
    with pytest.raises(Exception):
        SimpleSerializable.deserialize({
            'FooBar': _foo_bar_val,
            'FooBaz': 'invalid_type_value',
        })

    with pytest.raises(Exception):
        SimpleSerializable.deserialize({
            'FooBar': 3,
            'FooBaz': _foo_baz_val,
        })


def test_extra_field():
    with pytest.raises(Exception):
        SimpleSerializable.deserialize({
            'FooBar': _foo_bar_val,
            'FooBaz': _foo_baz_val,
            'ExtraField': None,
        })


class OptionalSerializable(rv.Serializable):

    foo_bar = rv.serializable.fields.Str(optional=True)
    foo_baz = rv.serializable.fields.Int(optional=True, default=3)


def test_optional():
    s = OptionalSerializable.deserialize({})
    assert s.foo_bar is None
    assert s.foo_baz == 3
