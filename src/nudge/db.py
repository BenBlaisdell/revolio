import flask_sqlalchemy
from nudge.orm import EntityOrm


def create_db(app, db_uri):
    app.config.update(
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_DATABASE_URI=db_uri,
    )

    return flask_sqlalchemy.SQLAlchemy(app)


def recreate_tables(engine):
    drop_tables(engine)
    create_tables(engine)


def create_tables(engine):
    EntityOrm.metadata.create_all(bind=engine)


def drop_tables(engine):
    EntityOrm.metadata.create_all(bind=engine)
