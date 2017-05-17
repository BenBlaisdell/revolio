import nudge.manager.stack
from nudge.manager.context import Stack


def build_template(ctx, s):
    if s == Stack.WEB:
        return nudge.manager.stack.web.build_template(ctx)
    if s == Stack.REPO:
        return nudge.manager.stack.repo.build_template(ctx)

    raise Exception('No builder for stack type: {}'.format(s))
