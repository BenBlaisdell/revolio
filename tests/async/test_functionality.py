import datetime as dt
import json
import os
from pathlib import Path

import pytest

from nudge.core.context import NudgeContext
from nudge.core.entity.subscription import SqsEndpoint
from nudge.core.entity import Batch, Subscription
from nudge.core.entity.element import Element


S3_CONFIG_URI = json.loads(os.environ['S3_CONFIG_URI'])
ENDPOINT_QUEUE_URL = json.loads(os.environ['ENDPOINT_QUEUE_URL'])


@pytest.fixture(scope='function')
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
        # todo: why does this call prevent tests from finishing
        # nudge.db.drop_tables()


def test_functionality(nudge):
    b = 'dummy-bucket'
    p = 'a/b/c'

    sub = nudge.subscribe(
        bucket=b,
        prefix=p,
        regex=None,
        trigger=Subscription.Trigger(
            threshold=50,
            endpoint=SqsEndpoint(
                queue_url=ENDPOINT_QUEUE_URL,
            ),
        ),
    )

    assert isinstance(sub, Subscription)

    ((elem1, batch1),) = nudge.handle_object_created(
        bucket=b,
        key=str(Path(p) / 'dummy-file-1.txt'),
        size=25,
        created=dt.datetime.strptime('2017-05-15 01:00:00', '%Y-%m-%d %H:%M:%S'),
    )

    assert elem1.state == Element.State.Unconsumed
    assert batch1 is None

    ((elem2, batch2),) = nudge.handle_object_created(
        bucket=b,
        key=str(Path(p) / 'dummy-file-2.txt'),
        size=25,
        created=dt.datetime.strptime('2017-05-15 02:00:00', '%Y-%m-%d %H:%M:%S'),
    )

    assert elem2.state == elem1.state == Element.State.Batched
    assert isinstance(batch2, Batch)

    nudge.consume(sub.id, batch2.id)
    assert elem2.state == elem1.state == Element.State.Consumed
