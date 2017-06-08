import json
import os
import pathlib as pl
import traceback

import flask
import nudge.core.context


class App:

    def __init__(self, ctx, flask_config, db, log):
        self._ctx = ctx
        self._log = log

        self._app = flask.Flask('nudge')
        self._app.config.update(**flask_config)

        functions = [
            ctx.attach_trigger,
            ctx.backfill,
            ctx.consume,
            ctx.get_batch_elems,
            ctx.get_sub_batches,
            ctx.handle_object_created,
            ctx.subscribe,
            ctx.unsubscribe,
        ]

        for f in functions:
            self._add_function(f)

        self._log.info('Adding endpoint: CheckHealth')
        self._app.add_url_rule(
            '/api/1/call/CheckHealth/',
            'CheckHealth',
            lambda: 'Healthy',
            methods=['GET'],
        )

        @self._app.errorhandler(500)
        def log_exception(exception):
            tb = traceback.format_exc()
            self._log.warning(tb)
            return tb, 500

        db.init_app(self._app)
        self._db = db

    def __call__(self, environ, start_response):
        """Start app under uwsgi"""
        # with self._app.app_context():
        #     self._db.create_tables()

        return self.flask_app(environ, start_response)

    def run(self):
        # with self._app.app_context():
        #     self._db.create_tables()

        self._app.run()

    @property
    def config(self):
        return self._app.config

    @property
    def flask_app(self):
        return self._app

    def _add_function(self, f):
        endpoint = f.url_path
        self._log.info('Adding endpoint: {}'.format(endpoint))
        self._app.add_url_rule(
            endpoint,
            f.name,
            lambda: self._handle_request(f),
            methods=['POST'],
        )

    def _handle_request(self, f):
        request = flask.request.get_json(force=True)
        result = f.handle_request(request)

        # commit for safety
        # todo: auto-commit all functions
        self._db.commit()

        return json.dumps(result)


if __name__ == '__main__':
    ctx = nudge.core.context.NudgeContext(
        json.loads(os.environ['S3_CONFIG_URI']),
        flask_config={
            'DEBUG': True,
        }
    )

    ctx.app.run()
