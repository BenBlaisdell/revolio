import abc


class Function(metaclass=abc.ABCMeta):

    def __init__(self, ctx):
        super().__init__()
        self._ctx = ctx

    @property
    def name(self):
        return type(self).__name__

    @abc.abstractmethod
    def format_request(self, *args, **kwargs):
        return {}

    @abc.abstractmethod
    def handle_request(self, request):
        return {
            'Message': self(),
        }

    @abc.abstractmethod
    def __call__(self, *args, **kwargs):
        return 'Success'

    @property
    def url_prefix(self):
        return '/api/{}'.format(self.api_version)

    @property
    def api_version(self):
        return self._ctx.config['Web']['Version']

    @property
    def url_path(self):
        return '{prefix}/call/{name}/'.format(
            prefix=self.url_prefix,
            name=type(self).__name__,
        )

    @property
    def url(self):
        return 'http://{host}{path}'.format(
            host=self._ctx.config['Web']['RecordSetName'],
            path=self.url_path,
        )
