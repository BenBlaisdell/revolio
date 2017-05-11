from cached_property import cached_property

import nudge.app
import nudge.db
from nudge.function import FunctionDirectory


class NudgeContext:

    def __init__(self, db_uri, *, app_configs=None):
        self._app = nudge.app.create_app(
            ctx=self,
            configs=(app_configs or {}),
        )

        self._db = nudge.db.create_db(
            app=self._app,
            uri=db_uri,
        )

    def run(self):
        self._app.run()

    @property
    def app(self):
        return self._app

    @property
    def db(self):
        return self._db

    @property
    def functions(self):
        return FunctionDirectory(self.db.session)
