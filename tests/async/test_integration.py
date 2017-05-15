import pytest

from nudge.context import NudgeContext


@pytest.fixture()
def nudge():
    nudge = NudgeContext(
        's3://bblaisdell-ply-bucket/nudge-config.yaml',
        flask_config={
            'TESTING': True,
            'SQLALCHEMY_RECORD_QUERIES': True,
        },
    )

    with nudge.app.flask_app.app_context():
        # connection = nudge.db._engine.connect()
        # transaction = connection.begin()
        # options = dict(bind=connection, binds={})
        # session = nudge.db._db.create_scoped_session(options=options)
        # nudge.db._db.session = session

        yield nudge

        # transaction.rollback()
        # connection.close()
        # session.remove()


def test_integration(nudge):
    nudge.db.recreate_tables()
