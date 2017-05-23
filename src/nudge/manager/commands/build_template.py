import troposphere as ts

import nudge.manager.stacks
from nudge.manager.context import Stack


def build_template(ctx, s):
    config = ctx.get_architecture_config(s)
    r_group = _get_resource_group(s)(config)
    ctx.save_template(s, r_group.get_template())


def _get_resource_group(s):
    if s == Stack.WEB:
        return nudge.manager.stacks.web.WebResources
    elif s == Stack.REPO:
        return nudge.manager.stacks.repo.RepoResources
    elif s == Stack.S3:
        return nudge.manager.stacks.s3.S3Resources
    elif s == Stack.DB:
        return nudge.manager.stacks.db.DatabaseResources
    else:
        raise Exception('No builder for stack type: {}'.format(s))
