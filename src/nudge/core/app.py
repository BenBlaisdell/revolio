import revolio as rv
import revolio.app

import nudge.core.context


class App(rv.app.App):

    @property
    def _functions(self):
        return [
            self._ctx.attach_trigger,
            self._ctx.backfill,
            self._ctx.consume,
            self._ctx.create_batch,
            self._ctx.get_batch_elems,
            self._ctx.get_sub_batches,
            self._ctx.get_subscription,
            self._ctx.handle_object_created,
            self._ctx.subscribe,
            self._ctx.unsubscribe,
        ]


if __name__ == '__main__':
    ctx = nudge.core.context.NudgeCoreContext(
        flask_config={
            'DEBUG': True,
        }
    )

    ctx.app.run()
