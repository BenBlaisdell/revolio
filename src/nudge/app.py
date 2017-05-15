import json
import os

import flask

import nudge.context
from nudge import util
from nudge.endpoint import Endpoint


class App:

    def __init__(self, ctx, flask_config, db, log):
        self._log = log
        self._app = self._create_app(ctx, flask_config)
        db.init_app(self._app)

    @property
    def config(self):
        return self._app.config

    def run(self):
        self._app.run()

    @property
    def flask_app(self):
        return self._app

    def _create_app(self, ctx, config):
        app = flask.Flask('nudge')
        app.config.update(**config)

        for f in _api_functions:
            endpoint = '/api/1/call/{}/'.format(f.name)
            self._log.info('Adding endpoint: {}'.format(endpoint))
            app.add_url_rule(
                endpoint,
                f.name,
                lambda: json.dumps(f(ctx, flask.request.get_json(force=True))),
                methods=['POST'],
            )

        return app


_api_functions = []


class ApiFunction:

    @property
    def name(self):
        return self._name

    def __init__(self, name, handler):
        self._name = name
        self._handler = handler

    def __call__(self, ctx, request):
        result = self._handler(ctx, request)
        return result if (result is not None) else {'Message': 'Success'}


def api_function(name=None):

    def decorator(fn):
        _api_functions.append(ApiFunction(
            name=name or util.snake_to_camel(fn.__name__),
            handler=fn,
        ))

        return fn

    return decorator


@api_function()
def subscribe(ctx, request):
    sub = ctx.subscribe(
        bucket=request['Bucket'],
        prefix=request.get('Prefix', None),
        endpoint=Endpoint(),
        regex=request.get('Regex', None),
        threshold=request.get('Threshold', None),
    )

    return {
        'SubscriptionId': sub.id,
    }


@api_function()
def handle_object_created(ctx, request):
    return {
        'MatchingSubscriptions': {
            elem.sub_id: {
                'ElementId': elem.id,
                'Triggered': triggered,
            }
            for elem, triggered in ctx.handle_obj_created(
                bucket=request['Bucket'],
                key=request['Key'],
                size=request['Size'],
                created=request['Created'],
            )
        },
    }


@api_function()
def consume(ctx, request):
    ctx.consume(
        elem_ids=request['ElementIds'],
    )


@api_function()
def unsubscribe(ctx, request):
    ctx.unsubscribe(
        sub_id=request['SubscriptionId'],
    )


if __name__ == '__main__':
    ctx = nudge.context.NudgeContext(
        os.environ['S3_CONFIG_URI'],
        flask_config={
            'DEBUG': True,
        }
    )

    ctx.app.run()
