import revolio as rv
import revolio.app

import nudge.core.context


class App(rv.app.App):

    def __init__(self, ctx, flask_config, db):

        functions = [
            ctx.attach_trigger,
            ctx.backfill,
            ctx.consume,
            ctx.create_batch,
            ctx.get_batch_elems,
            ctx.get_sub_batches,
            ctx.get_subscription,
            ctx.handle_object_created,
            ctx.subscribe,
            ctx.unsubscribe,
        ]

        self._setup(functions, flask_config, db)


if __name__ == '__main__':
    ctx = nudge.core.context.NudgeCoreContext(
        flask_config={
            'DEBUG': True,
        }
    )

    ctx.app.run()
