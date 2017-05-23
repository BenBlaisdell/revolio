import os

import nudge.context

ctx = nudge.context.NudgeContext(
    os.environ['S3_CONFIG_URI'],
    flask_config={
        'DEBUG': True,
    }
)

app = ctx.app.flask_app
