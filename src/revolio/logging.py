import revolio

import logging
import uuid

import flask


# Generate a new request ID, optionally including an original request ID
def generate_request_id(original_id=''):
    new_id = uuid.uuid4()

    if original_id:
        new_id = f'{original_id},{new_id}'

    return new_id


# Returns the current request ID or a new one if there is none
# In order of preference:
#   * If we've already created a request ID and stored it in the flask.g context local, use that
#   * If a client has passed in the X-Request-Id header, create a new ID with that prepended
#   * Otherwise, generate a request ID and store it in flask.g.request_id
def request_id():
    if getattr(flask.g, 'request_id', None):
        return flask.g.request_id

    headers = flask.request.headers
    original_request_id = headers.get("X-Request-Id")
    new_uuid = generate_request_id(original_request_id)
    flask.g.request_id = new_uuid

    return new_uuid


class RequestIdFilter(logging.Filter):

    def __init__(self, id_getter):
        super().__init__()
        self._id_getter = id_getter

    def filter(self, record):
        id = self._id_getter()
        record.request_id = id if (id is not None) else 'setup'
        return True


class FlaskRequestIdFilter(RequestIdFilter):

    def __init__(self):
        super().__init__(lambda: request_id() if flask.has_request_context() else None)


class WorkerRequestIdFilter(RequestIdFilter):

    def __init__(self, worker):
        super().__init__(lambda: worker.transaction_id)


class Formatter(logging.Formatter):

    def __init__(self):
        super().__init__('%(asctime)s - %(request_id)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s')

    def format(self, record):
        # \r keeps the record intact in cloudwatch
        # appears as a space when condensed and a new line when expanded
        record.msg = record.msg.replace('\n', '\r')
        return super(Formatter, self).format(record)


def init_flask(module, *, sqlalchemy_level=logging.DEBUG):
    h = logging.StreamHandler()
    h.setLevel(logging.DEBUG)
    h.addFilter(FlaskRequestIdFilter())
    h.setFormatter(Formatter())

    for name in [module.__name__, revolio.__name__]:
        _init_logger(name, h, logging.DEBUG)

    if sqlalchemy_level is not None:
        _init_logger('sqlalchemy.engine', h, sqlalchemy_level)


def _init_logger(name, h, level):
    l = logging.getLogger(name)
    l.setLevel(level)
    l.addHandler(h)
