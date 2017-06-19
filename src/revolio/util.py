import json
import re

import sqlalchemy as sa


first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')


def camel_to_snake(name):
    s1 = first_cap_re.sub(r'\1_\2', name)
    return all_cap_re.sub(r'\1_\2', s1).lower()


def snake_to_camel(name):
    return ''.join(map(str.capitalize, name.split('_')))


def log_dumps(obj):
    """Dump object to json to be logged."""
    return json.dumps(obj, separators=(',\r', ': '))

