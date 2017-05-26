import os

import nudge.core.context

ctx = nudge.core.context.NudgeContext(
    os.environ['S3_CONFIG_URI'],
    flask_config={
        'DEBUG': True,
    }
)

app = ctx.app.flask_app
