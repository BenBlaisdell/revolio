import os

from flask import json

import nudge
from nudge.core.context import NudgeContext


if __name__ == '__main__':
    ctx = nudge.core.context.NudgeContext(
        json.loads(os.environ['S3_CONFIG_URI']),
    )

    with ctx.app.flask_app.app_context():
        ctx.db.drop_tables()
