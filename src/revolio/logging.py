import revolio

import logging
import uuid

import flask


# Generate a new request ID, optionally including an original request ID
def generate_request_id(original_id=''):
    new_id = uuid.uuid4()

    if original_id:
        new_id = "{},{}".format(original_id, new_id)

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
    # This is a logging filter that makes the request ID available for use in
    # the logging format. Note that we're checking if we're in a request
    # context, as we may want to log things before Flask is fully loaded.
    def filter(self, record):
        record.request_id = request_id() if flask.has_request_context() else 'setup'
        return True


class Formatter(logging.Formatter):

    def __init__(self, flask=False):
        f = ['%(asctime)s']

        if flask:  # must have RequestIdFilter attached
            f.append('%(request_id)s')

        f.append('%(name)s:%(lineno)d')
        f.append('%(levelname)s')
        f.append('%(message)s')

        super().__init__(' - '.join(f))

    def format(self, record):
        # \r keeps the record intact in cloudwatch
        # appears as a space when condensed and a new line when expanded
        record.msg = record.msg.replace('\n', '\r')
        return super(Formatter, self).format(record)


def init(module, flask=False):
    h = logging.StreamHandler()
    h.setLevel(logging.DEBUG)

    if flask:
        h.addFilter(RequestIdFilter())

    h.setFormatter(Formatter(flask=flask))

    for name in [module.__name__, revolio.__name__, 'sqlalchemy.engine']:
        l = logging.getLogger(name)
        l.setLevel(logging.DEBUG)
        l.addHandler(h)
