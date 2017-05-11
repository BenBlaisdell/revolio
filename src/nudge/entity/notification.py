import uuid


class Notification(Entity):

    @property
    def bucket(self):
        return self._bucket

    @property
    def prefix(self):
        return self._prefix

    @property
    def c_id(self):
        return self._c_id

    @staticmethod
    def create(b, p):
        return Notification(
            bucket=b,
            prefix=p,
            c_id='nudge-subscription-{}'.format(str(uuid.uuid4())),
        )

    def to_orm(self):
        return NotificationOrm(
            bucket=self.bucket,
            prefix=self.prefix,
            c_id=self.c_id,
        )

    @staticmethod
    def from_orm(orm):
        return Notification(
            bucket=orm.bucket,
            prefix=orm.prefix,
            c_id=orm.c_id,
        )

    def __init__(self, bucket, prefix, c_id):
        super(Notification, self).__init__()
        self._bucket = bucket
        self._prefix = prefix
        self._c_id = c_id
