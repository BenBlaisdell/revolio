import boto3
from cached_property import cached_property


class Sqs:

    def __init__(self):
        super().__init__()

    @cached_property
    def _client(self):
        return boto3.client('sqs')

    def get_queue_arn(self, url):
        r = self._client.get_queue_attributes(
            QueueUrl=url,
            AttributeNames=['QueueArn'],
        )

        return r['Attributes']['QueueArn']
