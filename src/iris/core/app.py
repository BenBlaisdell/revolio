import logging

import revolio as rv
import revolio.app

import iris.core.context


class App(rv.app.App):

    def __init__(self, ctx, flask_config, db):

        functions = [
            ctx.add_listener,
            ctx.remove_listener,
        ]

        self._setup(functions, flask_config, db)


if __name__ == '__main__':
    ctx = iris.core.context.IrisContext(
        sqlalchemy_level=logging.DEBUG,
        flask_config={
            'DEBUG': True,
        }
    )

    ctx.app.run()
