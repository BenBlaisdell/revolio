import logging

import revolio as rv
import revolio.app

import iris.core.context


class App(rv.app.App):

    @property
    def _functions(self):
        return [
            self._ctx.add_listener,
            self._ctx.remove_listener,
        ]


if __name__ == '__main__':
    ctx = iris.core.context.IrisContext(
        sqlalchemy_level=logging.DEBUG,
        flask_config={
            'DEBUG': True,
        }
    )

    ctx.app.run()
