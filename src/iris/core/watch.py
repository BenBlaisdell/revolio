class WatchService:

    def __init__(self, nfn_srv, s3, db, queue):
        super(WatchService, self).__init__()
        self._nfn_srv = nfn_srv
        self._s3 = s3
        self._db = db
        self._queue = queue

    def ensure_watched(self, s):
        n = Notification.create(s.bucket, s.prefix)
        if not self._is_watched(n):
            consolidated = self._consolidate_notifications(n)
            self._update_s3_configs(n, consolidated)

    def _is_watched(self, n):
        return self._nfn_srv.get_covering_notification(n) is not None

    def _consolidate_notifications(self, n):
        covered = self._nfn_srv.get_covered_notifications(n)
        for covered_n in covered:
            self._db.delete_entity(covered_n)

        self._db.create_entity(n)
        return covered

    def _update_s3_configs(self, nfn, consolidated_nfns):
        n_configs = self._s3.get_notification_configs(nfn.bucket)
        topic_n_configs = {c['Id']: c for c in n_configs['TopicConfigurations']}

        # remove the old configs
        for n in consolidated_nfns:
            topic_n_configs.pop(n.c_id)

        # add the new config
        assert nfn.c_id not in topic_n_configs
        topic_n_configs[nfn.c_id] = self._get_topic_config(nfn)

        # update the configs
        n_configs['TopicConfigurations'] = topic_n_configs.values()
        self._s3.put_notification_configs(nfn.bucket, n_configs)

    def _get_topic_config(self, nfn):
        c = {
            'Id': nfn.c_id,
            'QueueArn': self._queue,
            'Events': ['s3:ObjectCreated:*'],
        }

        if nfn.prefix is not None:
            c['Filter'] = {
                'Key': {
                    'FilterRules': [{
                        'Name': 'prefix',
                        'Value': nfn.prefix,
                    }],
                },
            }

        return c
