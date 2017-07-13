import json
import logging

import boto3

from cached_property import cached_property

from iris.core.entity.listener import SqsEndpoint


_log = logging.getLogger(__name__)


class Sns:

    def __init__(self):
        super().__init__()

    @cached_property
    def _client(self):
        return boto3.client('sns')

    def __getattr__(self, item):
        return getattr(self._client, item)

    def subscribe_handler(self, nfn, hlr):
        """Subscribe a handler to an SNS topic."""
        _log.info(f'Subscribing to {nfn.topic_arn} with {hlr.protocol} protocol: {hlr.endpoint}')

        r = self._client.subscribe(
            TopicArn=nfn.topic_arn,
            Protocol=hlr.protocol,
            Endpoint=hlr.endpoint,
        )

        sub_arn = r['SubscriptionArn']
        nfn.topic_subscriptions[hlr.id] = sub_arn
        return sub_arn

    def unsubscribe_handler(self, nfn, hlr):
        nfn.topic_subscriptions.pop(hlr.id)
        self._client.unsubscribe(
            SubscriptionArn=nfn.topic_subscriptions[hlr.id],
        )
