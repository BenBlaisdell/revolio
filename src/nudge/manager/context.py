import datetime as dt
import enum
import json
import os
import random
import string
import uuid

from cached_property import cached_property
import ruamel.yaml as ryaml

from nudge.manager.infrastructure.env import EnvResources


class Component(enum.Enum):
    APP = ('web', 'app')
    NGX = ('web', 'ngx')
    S3E = ('wrk', 's3e')
    DEF = ('wrk', 'def')


class EnvName(enum.Enum):
    DEV = 'dev'
    STG = 'stg'
    PRD = 'prd'


UNCHANGED_PARAM = object()


class NudgeCommandContext(object):

    def __init__(self, data_path, resources_path, env_name):
        super(NudgeCommandContext, self).__init__()
        self._d_path = data_path
        self._r_path = resources_path
        self._env = env_name

    @cached_property
    def transaction_id(self):
        return str(uuid.uuid4())

    @cached_property
    def _base_data_path(self):
        return os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')

    def get_repo_uri(self, c):
        a, b = c.value
        return self.stack_config['Ecr']['Repos'][a.capitalize()][b.capitalize()]['Url']

    def get_dockerfile_path(self, component):
        a, b = component.value
        return self._get_data_path('dockerfiles', 'Dockerfile-{}-{}'.format(a, b))

    def save_template(self, template):
        self._save_resource('stack/template.json', template)

    @cached_property
    def revolio_config(self):
        return self.stack_config['Revolio']

    @cached_property
    def template_key(self):
        return 'nudge-template-{timestamp}-{uuid}'.format(
            timestamp=dt.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'),
            uuid=uuid.uuid4(),
        )

    @cached_property
    def stack(self):
        return EnvResources(self, self.stack_config)

    @cached_property
    def stack_config(self):
        return self._get_yaml_resource('stack/config.yaml')

    @cached_property
    def raw_stack_config(self):
        return self._get_string_resource('stack/config.yaml')

    @cached_property
    def stack_template(self):
        return self._get_string_resource('stack/template.json')

    @cached_property
    def stack_name(self):
        return self.stack_resources['StackName']

    @cached_property
    def stack_resources(self):
        return self._get_yaml_resource('stack/resources.yaml')

    def get_stack_parameters(self, initial):
        return self.stack.get_parameters()

    @cached_property
    def stack_tags(self):
        return self.stack_config['Tags']

    @cached_property
    def base_path(self):
        return os.path.abspath(os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            '..',  # nudge/src/nudge/
            '..',  # nudge/src/
            '..',  # nudge/
        ))

    @cached_property
    def stack_change_set_name(self):
        return 'nudge-change-set-{timestamp}-{uuid}'.format(
            timestamp=dt.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'),
            uuid=uuid.uuid4(),
        )

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
        return os.path.join(self._r_path, 'envs', self._env.value.lower(), name)

    def _get_data_path(self, *args):
        return os.path.join(self._base_data_path, *args)


def _generate_db_password():
    char_set = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return ''.join(random.SystemRandom().choice(char_set) for _ in range(32))
