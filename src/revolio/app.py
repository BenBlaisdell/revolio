import json
import logging
import traceback

import flask


_log = logging.getLogger(__name__)


class App:

    def _setup(self, functions, flask_config, db):

        self._app = flask.Flask('nudge')
        self._app.config.update(**flask_config)

        for f in functions:
            self._add_function(f)

        _log.info('Adding endpoint: CheckHealth')
        self._app.add_url_rule(
            '/api/1/call/CheckHealth',
            'CheckHealth',
            lambda: 'Healthy',
            methods=['GET'],
        )

        # @self._app.errorhandler(500)
        # def log_exception(exception):
        #     tb = traceback.format_exc()
        #     _log.warning(tb)
        #     return tb, 500

        db.init_app(self._app)

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
        _log.info(f'Adding endpoint: {endpoint}')
        self._app.add_url_rule(
            endpoint,
            f.name,
            lambda: self._handle_request(f),
            methods=['POST'],
        )

    def _handle_request(self, f):
        request = flask.request.get_json(force=True)

        _log.info('Handling request: {}'.format(f.name))

        try:
            code, result = 200, f.handle_request(request)
        except:
            e = traceback.format_exc()
            _log.warning(e)
            code, result = 500, {
                'Traceback': e.split('\n'),
            }

        return json.dumps(result), code
