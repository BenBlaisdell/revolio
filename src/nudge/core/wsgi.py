import os

from flask import json

import nudge.core.context

ctx = nudge.core.context.NudgeContext(
    json.loads(os.environ['S3_CONFIG_URI']),
)

app = ctx.app
