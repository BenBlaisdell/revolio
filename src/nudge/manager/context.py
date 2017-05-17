import enum
import json
import os

from cached_property import cached_property
import ruamel.yaml as ryaml


class Component(enum.Enum):
    FLASK = 'flask'
    NGINX = 'nginx'


class EnvName(enum.Enum):
    DEV = 'dev'
    STAGE = 'stage'
    PROD = 'prod'


class Stack(enum.Enum):
    WEB = 'web'
    REPO = 'repo'


class NudgeCommandContext(object):

    def __init__(self, data_path, resources_path, env_name):
        super(NudgeCommandContext, self).__init__()
        self._d_path = data_path
        self._r_path = resources_path
        self._env = env_name

    @cached_property
    def _base_data_path(self):
        return os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')

    def _get_data_path(self, *args):
        return os.path.join(self._base_data_path, *args)

    def get_dockerfile_path(self, component):
        return self._get_data_path('dockerfiles', 'Dockerfile-{}'.format(component.name.lower()))

    def get_docker_repo_uri(self, component):
        return self.architecture_config['{}Image'.format(component.name.capitalize())]

    def save_template(self, template):
        self._save_resource('stacks/web/template.json', template)

    @cached_property
    def web_template(self):
        return self._get_string_resource('stacks/web/template.json')

    @cached_property
    def stack_name(self):
        return self._get_yaml_resource('stacks/web/resources.yaml')['StackName']

    @cached_property
    def service_config(self):
        return self._get_yaml_resource('config.yaml')

    @cached_property
    def architecture_config(self):
        return self._get_yaml_resource('stacks/web/config.yaml')

    @cached_property
    def base_path(self):
        return os.path.abspath(os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            '..',  # nudge/src/nudge/
            '..',  # nudge/src/
            '..',  # nudge/
        ))

    # private

    def _get_yaml_resource(self, filename):
        return self._get_resource(filename, lambda f: ryaml.load(f, Loader=ryaml.Loader))

    def _get_json_resource(self, filename):
        return self._get_resource(filename, lambda f: json.load(f))

    def _get_string_resource(self, filename):
        return self._get_resource(filename, lambda f: f.read())

    def _get_resource(self, filename, parse):
        with open(self._get_resource_path(filename)) as f:
            return parse(f)

    def _save_resource(self, filename, data):
        with open(self._get_resource_path(filename), 'w') as f:
            f.write(data)

    def _get_resource_path(self, name):
        return os.path.join(self._r_path, 'envs', self._env.name.lower(), name)
