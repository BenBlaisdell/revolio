import json
import logging

import revolio as rv
import revolio.entity
import revolio.function
import revolio.serializable
from revolio.sqlalchemy import autocommit

from iris.core.entity import Notification, Listener


_log = logging.getLogger(__name__)


class RemoveListener(rv.function.Function):

    api_version = '1'

    def __init__(self, ctx, lst_srv, nfn_srv, hlr_srv, s3, sns, db):
        super().__init__(ctx)
        self._lst_srv = lst_srv
        self._nfn_srv = nfn_srv
        self._hlr_srv = hlr_srv
        self._s3 = s3
        self._sns = sns
        self._db = db

    def format_request(self, id):
        return {
            'Id': id,
        }

    @rv.function.validate(
        id=rv.serializable.fields.Str(),
    )
    def handle_request(self, request):

        # make call

        deactivated, nfns = self(
            id=request.id,
        )

        # format response

        return {
            'DeactivatedNotification': deactivated,
            'UnconsolidatedNotifications': None if not deactivated else [n.id for n in nfns],
        }

    @autocommit
    def __call__(self, id):
        lst = self._get_listener(id)

        _log.info(f'Deactivating {lst}')
        lst.state = Listener.State.DEACTIVATED

        if len(lst.notification.direct_listeners) == 0:
            # deactivated the only listener depending on this path
            # deactivate the notification and make sure any subpaths are watched
            return True, self._deactivate_notifications(lst.notification)

        if lst.handler not in self._hlr_srv.get_notification_handlers(lst.notification):
            # no other listener on some subpath of this notification has the same handler as the deactivated listener
            # remove the handler from the notification's sns topic
            self._sns.unsubscribe_handler(lst.notification, lst.handler)

        return False, None

    def _deactivate_notifications(self, nfn):
        _log.info(f'Unconsolidating {nfn}')
        nfn.state = Notification.State.DEACTIVATED

        self._db.flush()

        nfns = [
            self._create_notification(nfn.bucket, prefix, listeners)
            for prefix, listeners in self._get_root_watched_subprefixes(nfn.bucket, nfn.prefix).items()
        ]

        nfn.data = dict(unconsolidated=[n.id for n in nfns])

        try:
            self._db.flush()
        except:
            self._delete_notification_topics(nfns)
            raise

        for n in nfns:
            for hlr in self._hlr_srv.get_notification_handlers(n):
                self._sns.subscribe_handler(n, hlr)

        try:
            self._update_bucket_notification_configs(nfn, nfns)
        except:
            _log.error(f'Failed to unconsolidate notifications')
            self._delete_notification_topics(nfns)
            raise

        return nfns

    def _delete_notification_topics(self, nfns):
        for n in nfns:
            self._sns.delete_notification_topic(n)

    def _get_root_watched_subprefixes(self, bucket, prefix):
        listeners = self._lst_srv.get_covered_listeners(bucket, prefix)
        roots = {}

        while len(listeners) > 0:
            lst = listeners.pop(0)
            roots[lst.prefix] = [lst]

            while len(listeners) > 0 and listeners[0].prefix.startswith(lst.prefix):
                roots[lst.prefix].append(listeners.pop(0))

        return roots

    def _get_listener(self, id):
        lst = self._lst_srv.get_listener(id)

        if lst is None:
            raise Exception(f'No listener with id {id}')

        if lst.state is Listener.State.DEACTIVATED:
            raise Exception('Listener')

        return lst

    def _update_bucket_notification_configs(self, nfn, nfns):
        print(nfn, nfns)
        with self._s3.topic_notification_configs(nfn.bucket) as configs:
            configs.pop(nfn.topic_config_id)

            for n in nfns:
                assert n.topic_config_id not in configs
                configs[n.topic_config_id] = n.topic_notification_config

    def _get_handlers(self, nfns):
        return self._db \
            .query(Notification.topic_arn, Notification.handlers) \
            .filter(Notification.id.in_([n.id for n in nfns])) \
            .all()

    def _create_notification(self, bucket, prefix, listeners):
        nfn_id = rv.entity.gen_id()

        for lst in listeners:
            lst.notification_id = nfn_id

        return self._db.add(Notification(
            id=nfn_id,
            state=Notification.State.ACTIVE,
            bucket=bucket,
            prefix=prefix,
            topic_config_id=f'iris-{nfn_id}',
            topic_arn=self._create_notification_topic(nfn_id, bucket),
        ))

    def _create_notification_topic(self, nfn_id, bucket):
        """Create an SNS topic for the given notification."""
        topic_arn = self._sns.create_topic(Name=f'iris-{nfn_id}')['TopicArn']

        self._sns.set_topic_attributes(
            TopicArn=topic_arn,
            AttributeName='Policy',
            AttributeValue=json.dumps({
                'Version': '2012-10-17',
                'Id': 'allow-s3-notifications',
                'Statement': [{
                    'Effect': 'Allow',
                    'Principal': {'AWS': '*'},
                    'Action': ['SNS:Publish'],
                    'Resource': topic_arn,
                    'Condition': {
                        'ArnLike': {'aws:SourceArn': f'arn:aws:s3:*:*:{bucket}'},
                    },
                }],
            }),
        )

        return topic_arn