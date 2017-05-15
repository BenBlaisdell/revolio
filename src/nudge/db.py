import flask_sqlalchemy
from nudge.orm import EntityOrm


class Database:

    def __init__(self, log, db_uri):
        self._db_uri = db_uri
        self._db = flask_sqlalchemy.SQLAlchemy()

    @property
    def _session(self):
        return self._db.session

    @property
    def _engine(self):
        return self._db.engine

    def init_app(self, app):
        app.config.update(
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SQLALCHEMY_DATABASE_URI=self._db_uri,
        )

        self._db.init_app(app)

    def recreate_tables(self):
        self.drop_tables()
        self.create_tables()

    def create_tables(self):
        EntityOrm.metadata.create_all(bind=self._engine)

    def drop_tables(self):
        EntityOrm.metadata.drop_all(bind=self._engine)

    def add(self, entity):
        self._session.add(entity.orm)

    def commit(self):
        self._session.commit()

    def query(self, *args, **kwargs):
        return self._session.query(*args, **kwargs)

    def flush(self):
        self._session.flush()
