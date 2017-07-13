import logging

import flask_sqlalchemy
import sqlalchemy as sa
import sqlalchemy.orm.exc


_log = logging.getLogger(__name__)


class Database:

    def __init__(self, db_uri, entity):
        self._db_uri = db_uri
        self._db = flask_sqlalchemy.SQLAlchemy()
        self._entity = entity

    @property
    def _session(self):
        return self._db.session

    @property
    def _engine(self):
        return self._db.engine

    def init_app(self, app):
        app.config.update(
            SQLALCHEMY_ECHO=False,  # logger output captured
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SQLALCHEMY_DATABASE_URI=self._db_uri,
        )

        self._db.init_app(app)

    def recreate_tables(self):
        self.drop_tables()
        self.create_tables()

    def create_tables(self):
        _log.info('Creating tables')
        self._entity.metadata.create_all(bind=self._engine)

    def drop_tables(self):
        _log.info('Dropping tables')
        # reflect to include tables not defined in code
        meta = sa.MetaData()
        meta.reflect(bind=self._engine)
        for table in reversed(meta.sorted_tables):
            _log.info(f'Dropping table: {table.name}')
            table.drop(bind=self._engine)

    def add(self, entity):
        _log.info(f'Creating entity {entity}')
        self._session.add(entity)
        return entity

    def commit(self):
        self._session.commit()

    def query(self, *args, **kwargs):
        return self._session.query(*args, **kwargs)

    def flush(self):
        self._session.flush()

    def rollback(self):
        self._session.rollback()

    def get_or_create(self, model, **kwargs):
        try:
            return self._session \
                .query(model) \
                .filter_by(**kwargs) \
                .one()
        except sa.orm.exc.NoResultFound:
            return self.add(model(**kwargs))
