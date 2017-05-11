from cached_property import cached_property

import nudge.app
import nudge.db


class NudgeContext:

    def __init__(self, app_configs, db_uri):
        self._db_uri = db_uri
        self._app_configs = app_configs

    @cached_property
    def db_uri(self):
        return self._db_uri

    @cached_property
    def app_configs(self):
        return self._app_configs

    @cached_property
    def app(self):
        return nudge.app.create_app(self.app_configs)

    @cached_property
    def db(self):
        return nudge.db.create_db(
            self.app,
            self.db_uri,
        )
