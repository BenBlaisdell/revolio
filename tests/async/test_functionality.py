import os
from pathlib import Path

import pytest

from nudge.context import NudgeContext
from nudge.entity.element import Element


S3_CONFIG_URI = os.environ['S3_CONFIG_URI']
ENDPOINT_QUEUE_URL = os.environ['ENDPOINT_QUEUE_URL']


@pytest.fixture()
def nudge():
    nudge = NudgeContext(
        S3_CONFIG_URI,
        flask_config={
            'TESTING': True,
            'SQLALCHEMY_RECORD_QUERIES': True,
        },
    )

    with nudge.app.flask_app.app_context():
        nudge.db.recreate_tables()
        yield nudge


def test_functionality(nudge):
    b = 'dummy-bucket'
    p = 'a/b/c'

    nudge.subscribe(
        bucket=b,
        prefix=p,
        regex=None,
        threshold=50,
        endpoint=dict(
            Protocol='SQS',
            Parameters=dict(
                QueueUrl=ENDPOINT_QUEUE_URL,
            ),
        ),
    )

    ((elem1, triggered1),) = nudge.handle_obj_created(
        bucket=b,
        key=str(Path(p) / 'dummy-file-1.txt'),
        size=25,
        created='2017-05-15 01:00:00',
    )

    assert elem1.state == Element.State.Unconsumed
    assert not triggered1

    ((elem2, triggered2),) = nudge.handle_obj_created(
        bucket=b,
        key=str(Path(p) / 'dummy-file-2.txt'),
        size=25,
        created='2017-05-15 02:00:00',
    )

    assert elem2.state == elem1.state == Element.State.Sent
    assert triggered2

    nudge.consume([elem1.id, elem2.id])
    assert elem2.state == elem1.state == Element.State.Consumed
