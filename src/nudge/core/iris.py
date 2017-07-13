import json
import logging

import requests


_log = logging.getLogger(__name__)


class IrisClient:

    def __init__(self, config):
        super().__init__()
        endpoint = config['Iris']['Endpoint']
        version = config['Iris']['Version']
        self._base_url = f'{endpoint}/api/{version}/call'

    def add_listener(self, bucket, prefix, protocol, endpoint, *, tag=None):
        return self._post_json(
            'AddListener',
            {
                'Bucket': bucket,
                'Prefix': prefix,
                'Protocol': protocol,
                'Endpoint': endpoint,
                'Tag': tag,
            },
        )

    def remove_listener(self, id):
        return self._post_json(
            'RemoveListener',
            {
                'Id': id,
            },
        )

    def _post_json(self, f_name, data):
        url = f'{self._base_url}/{f_name}'
        f_data = json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))
        _log.debug(f'Sending iris call {url}\r{f_data}')
        r = requests.post(url, json=data)

        if r.status_code != 200:
            raise Exception('\n'.join([
                f'Iris call {f_name} failed with code {r.status_code}',
                json.dumps(r.json(), sort_keys=True, indent=4, separators=(',', ': ')),
            ]))

        return r.json()
