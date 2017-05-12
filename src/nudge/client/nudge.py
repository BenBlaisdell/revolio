import requests

class NudgeClient(object):
    def __init__(self, host, port=80, api_version=1):
        self._host = host
        self._port = port
        self._api_version = api_version
        self._base_url = 'http://{host}:{port}/api/{version}/call/'.format(
            host=self._host,
            port=self._port,
            version=self._api_version
        ) + '{endpoint}/'

    def Subscribe(self, Bucket, Prefix, Endpoint, Regex=None, Threshold=None):
        data = {
            'Bucket': Bucket,
            'Prefix': Prefix,
            'Endpoint': Endpoint,
            'Regex': Regex,
            'Threshold': Threshold
        }
        return self._post_json('Subscribe', data)

    def Unsubscribe(self, SubscriptionId):
        data = {
            'SubscriptionId': SubscriptionId
        }
        return self._post_json('Unsubscribe', data)

    def consume(self, ElementIds):
        data = {
            'ElementIds': ElementIds
        }
        return self._post_json('Consume', data)

    def handle_object_created(self, Bucket, Key, Size, Created):
        data = {
            'Bucket': Bucket,
            'Key': Key,
            'Size': Size,
            'Created': Created
        }
        return self._post_json('HandleObjectCreated', data)

    def _post_json(self, endpoint, data):
        return requests.post(self._base_url.format(endpoint=endpoint), json=data)