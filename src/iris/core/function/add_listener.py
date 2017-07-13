import json
import logging

import revolio as rv
import revolio.entity
import revolio.function
import revolio.serializable
from revolio.sqlalchemy import autocommit

from iris.core.entity import Handler, Listener, Notification


_log = logging.getLogger(__name__)


class AddListener(rv.function.Function):

    api_version = '1'

    def __init__(self, ctx, db, sns, nfn_srv, lst_srv, s3):
        super().__init__(ctx)
        self._db = db
        self._sns = sns
        self._nfn_srv = nfn_srv
        self._lst_srv = lst_srv
        self._s3 = s3

    def format_request(self, bucket, prefix, protocol, endpoint, *, tag=None):
        return {
            'Bucket': bucket,
            'Prefix': prefix,
            'Protocol': protocol,
            'Endpoint': endpoint,
            'Tag': tag,
        }

    @rv.function.validate(
        tag=rv.serializable.fields.Str(optional=True),
        bucket=rv.serializable.fields.Str(),
        prefix=rv.serializable.fields.Str(),
        protocol=rv.serializable.fields.Str(),
        endpoint=rv.serializable.fields.Str(),
    )
    def handle_request(self, request):

        # make call

        lst = self(
            bucket=request.bucket,
            prefix=request.prefix,
            protocol=request.protocol,
            endpoint=request.endpoint,
            tag=request.tag,
        )

        # format response

        return {
            'ListenerId': lst.id,
        }

    @autocommit
    def __call__(self, bucket, prefix, protocol, endpoint, *, tag=None):
        lst = Listener(
            id=rv.entity.gen_id(),
            state=Listener.State.ACTIVE,
            tag=tag,
            bucket=bucket,
            prefix=prefix,
            notification=self._get_covering_nfn(bucket, prefix),
            handler=self._db.get_or_create(
                Handler,
                protocol=protocol,
                endpoint=endpoint,
            ),
        )

        if lst.handler not in [l.handler for l in lst.notification.listeners]:
            self._sns.subscribe_handler(lst.notification, lst.handler)

        return self._db.add(lst)

    def _get_covering_nfn(self, bucket, prefix):
        """Return the notification watching this path or consolidate existing ones."""
        for _ in range(3):

            nfn = self._nfn_srv.get_covering_notification(bucket, prefix)
            if nfn is not None:
                return nfn

            try:
                return self._consolidate_nfns(bucket, prefix)
            except Exception as e:
                _log.error(f'Failed to consolidate notifications: {e}')
                self._db.rollback()

        raise Exception('Unable to retrieve covering notification')

    def _consolidate_nfns(self, bucket, prefix):
        """Create a new notification watching this path.
        
        Creates a new SNS topic, subscribes current handlers for all notifications that will be covered, and updates
        the S3 bucket notification configuration to send events to it.
        """
        _log.info(f'Watching path: s3://{bucket}/{prefix}')

        covered_nfns = self._nfn_srv.get_covered_notifications(bucket, prefix)
        _log.info(f'Consolidating notifications: {covered_nfns}')

        handlers = set(
            l.handler
            for n in covered_nfns
            for l in n.listeners
        )

        nfn_id = rv.entity.gen_id()
        nfn = self._db.add(Notification(
            id=nfn_id,
            state=Notification.State.ACTIVE,
            bucket=bucket,
            prefix=prefix,
            topic_config_id=f'iris-{nfn_id}',
            topic_arn=self._create_notification_topic(nfn_id, bucket),
        ))

        for c_nfn in covered_nfns:
            c_nfn.state = Notification.State.CONSOLIDATED
            c_nfn.data = {'consolidated_by': nfn.id}
            for lst in c_nfn.listeners:
                lst.notification = nfn

        try:
            self._db.flush()
        except:
            self._sns.delete_topic(TopicArn=nfn.topic_arn)
            raise

        for hlr in handlers:
            self._sns.subscribe_handler(nfn, hlr)

        try:
            self._update_bucket_notification_configs(nfn, covered_nfns)
        except:
            _log.error(f'Failed to consolidate s3 notification configs')
            self._sns.delete_topic(TopicArn=nfn.topic_arn)
            raise

        return nfn

    def _subscribe_handler(self, topic_arn, hlr):
        """Subscribe a handler to an SNS topic."""
        _log.info(f'Subscribing to {topic_arn} with {hlr.protocol} protocol: {hlr.endpoint}')
        self._sns.subscribe(
            TopicArn=topic_arn,
            Protocol=hlr.protocol,
            Endpoint=hlr.endpoint,
        )

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

    def _update_bucket_notification_configs(self, nfn, covered_nfns):
        """Replace old notification configurations with new consolidated one."""
        with self._s3.topic_notification_configs(nfn.bucket) as configs:

            assert nfn.topic_config_id not in configs
            configs[nfn.topic_config_id] = nfn.topic_notification_config

            for c_nfn in covered_nfns:
                configs.pop(c_nfn.topic_config_id)
