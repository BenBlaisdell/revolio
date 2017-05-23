import troposphere as ts

import nudge.manager.stack
from nudge.manager.context import Stack


def build_template(ctx, s):
    t = ts.Template()

    add_resources = _get_resource_adder(s)
    add_resources(t, ctx.get_architecture_config(s))

    ctx.save_template(s, t.to_json())


def _get_resource_adder(s):
    if s == Stack.WEB:
        return nudge.manager.stack.web.add_resources
    elif s == Stack.REPO:
        return nudge.manager.stack.repo.add_resources
    elif s == Stack.S3:
        return nudge.manager.stack.s3.add_resources
    else:
        raise Exception('No builder for stack type: {}'.format(s))
