import re

import sqlalchemy as sa


class Regex(sa.types.TypeDecorator):
    impl = sa.String

    def process_bind_param(self, value, dialect):
        if value is None:
            return None

        if isinstance(value, str):
            return value

        # assume type regex
        return value.pattern

    def process_result_value(self, value, dialect):
        if value is None:
            return None

        return re.compile(value)
