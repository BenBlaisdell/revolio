import os

import sqlalchemy

from nudge.orm import EntityOrm


if __name__ == '__main__':
    engine = sqlalchemy.create_engine('postgresql://{u}:{p}@{e}:5432/{db}'.format(
        e=os.environ['NUDGE_DB_ENDPOINT'],
        db=os.environ['NUDGE_DB_NAME'],
        u=os.environ['NUDGE_DB_USERNAME'],
        p=os.environ['NUDGE_DB_PASSWORD'],
    ))

    EntityOrm.metadata.drop_all(engine)
    EntityOrm.metadata.create_all(engine)
