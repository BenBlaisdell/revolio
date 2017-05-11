import json
import os

import flask

import nudge.context


def create_app(ctx, configs):
    app = flask.Flask('nudge')
    app.config.update(**configs)

    for name, fn in _functions.items():
        _add_function(app, name, fn, ctx)

    return app


def _add_function(app, name, fn, ctx):
    app.add_url_rule(
        '/api/1/call/{}/'.format(name),
        name,
        lambda: json.dumps(fn(ctx, flask.request.get_json(force=True))),
        methods=['POST'],
    )


_functions = {}


def api_function(name):

    def decorator(fn):
        assert name not in _functions
        _functions[name] = fn
        return fn

    return decorator


@api_function('Subscribe')
def subscribe(ctx, request):
    sub = ctx.subscribe(
        bucket=request['Bucket'],
        prefix=request['Prefix'],
        endpoint=request['Endpoint'],
        regex=request.get('Regex', None),
        threshold=request.get('Threshold', None),
    )

    return {
        'SubscriptionId': sub.id,
    }


@api_function('HandleObjectCreated')
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


@api_function('Consume')
def consume(ctx, request):
    ctx.consume(
        elem_ids=request['ElementIds'],
    )

    return {'Message': 'Success'}


@api_function('Unsubscribe')
def unsubscribe(ctx, request):
    ctx.unsubscribe(
        sub_id=request['SubscriptionId'],
    )

    return {'Message': 'Success'}


if __name__ == '__main__':
    ctx = nudge.context.NudgeContext(
        db_uri='postgresql://{u}:{p}@{e}:5432/{db}'.format(
            e=os.environ['NUDGE_DB_ENDPOINT'],
            db=os.environ['NUDGE_DB_NAME'],
            u=os.environ['NUDGE_DB_USERNAME'],
            p=os.environ['NUDGE_DB_PASSWORD'],
        ),
        app_configs={
            'DEBUG': True,
        }
    )

    ctx.app.run()
