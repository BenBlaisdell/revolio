import revolio as rv


_foo_baz_default = 3
_foo_qux_default = 5


class SimpleSerializable(rv.Serializable):

    foo_bar = rv.serializable.fields.Str(optional=True)
    foo_baz = rv.serializable.fields.Int(optional=True, default=_foo_baz_default)
    foo_qux = rv.serializable.fields.Int(optional=True, get_default=lambda: _foo_qux_default)


def test_optional():
    s = SimpleSerializable()

    assert s.foo_bar is None
    assert s.foo_baz == _foo_baz_default
    assert s.foo_qux == _foo_qux_default
