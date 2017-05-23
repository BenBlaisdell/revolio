import json
import os

import flask

import nudge.context
from nudge import util
from nudge.endpoint import Endpoint


class App:

    def __init__(self, ctx, flask_config, db, log):
        self._log = log

        self._app = flask.Flask('nudge')
        self._app.config.update(**flask_config)

        functions = [
            ctx.subscribe,
            ctx.handle_object_created,
            ctx.consume,
            ctx.unsubscribe,
        ]

        for f in functions:
            self._add_function(f)

        self._app.add_url_rule(
            '/api/1/call/CheckHealth/',
            'CheckHealth',
            lambda: 'Healthy',
            methods=['GET'],
        )

        db.init_app(self._app)

    @property
    def config(self):
        return self._app.config

    def run(self):
        self._app.run()

    @property
    def flask_app(self):
        return self._app

    def _add_function(self, f):
        name = type(f).__name__
        endpoint = '/api/1/call/{}/'.format(name)
        self._log.info('Adding endpoint: {}'.format(endpoint))
        self._app.add_url_rule(
            endpoint,
            name,
            lambda: json.dumps(f.handle_request(flask.request.get_json(force=True))),
            methods=['POST'],
        )


if __name__ == '__main__':
    ctx = nudge.context.NudgeContext(
        os.environ['S3_CONFIG_URI'],
        flask_config={
            'DEBUG': True,
        }
    )

    ctx.app.run()
