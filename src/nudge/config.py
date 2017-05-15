import re

from cached_property import cached_property
import ruamel.yaml as ryaml


class ConfigService:

    def __init__(self, log, s3, config_s3_uri):
        self._log = log
        self._s3 = s3
        self._config_s3_uri = config_s3_uri

    @cached_property
    def _config(self):
        return ryaml.load(self._raw_config, ryaml.Loader)

    @cached_property
    def _raw_config(self):
        self._log.info('Fetching S3 config: {}'.format(self._config_s3_uri))
        return self._s3.get_object(**_parse_s3_uri(self._config_s3_uri))['Body']

    def __getitem__(self, key):
        return self._config[key]


_s3_uri_re = re.compile(r'\As3://(?P<Bucket>.*?)/(?P<Key>.*)\Z')


def _parse_s3_uri(uri):
    return _s3_uri_re.match(uri).groupdict()
