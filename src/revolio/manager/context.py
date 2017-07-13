import abc
import base64
import datetime as dt
import enum
import itertools
import json
import logging
import os
import random
import string
import subprocess
import time
import uuid

import boto3
from cached_property import cached_property
import click
import ruamel.yaml as ryaml

import revolio as rv
import revolio.manager


UNCHANGED_PARAM = object()


# _directory[SERVICE][ENV] = CommandContext
_directory = {}


_log = logging.getLogger(__name__)


cf_client = boto3.client('cloudformation')
s3_client = boto3.client('s3')


class Env(enum.Enum):
    PROD = 'prd'
    STAGE = 'stg'
    DEV = 'dev'
    TEST = 'tst'


class RevolioCommandContext(metaclass=abc.ABCMeta):

    SERVICE = None
    env = None

    STACK = None
    ECR_STACK = None

    Component = None

    SERVICE_CONTEXT = None

    def recreate_tables(self):
        # todo: deal with env var config

        if (self.env in [Env.PROD, Env.STAGE]) and not self._prompt_user(f'recreate {self.env.name.lower()} tables'):
            return

        srv_ctx = self.SERVICE_CONTEXT()
        with srv_ctx.app.flask_app.app_context():
            srv_ctx.db.recreate_tables()

    @cached_property
    def stack(self):
        return self.STACK(self, self.stack_config)

    @property
    def project_name(self):
        return self.SERVICE[0]

    @property
    def project_tag(self):
        return self.SERVICE[1]

    @cached_property
    def ecr_stack(self):
        return self.ECR_STACK(self, self.stack_config['Ecr'])

    def __init__(self, resources_path):
        super(RevolioCommandContext, self).__init__()
        self._r_path = resources_path

    def __init_subclass__(cls):
        super().__init_subclass__()
        srv, env = cls.SERVICE[0] if cls.SERVICE else None, cls.env.name.lower() if cls.env else None

        if srv not in _directory:
            _directory[srv] = {}

        assert env not in _directory[srv]
        _directory[srv][env] = cls

    def build_template(self):
        self._save_resource('stack/template.json', self.stack.get_template())

    def create_stack(self):
        self._upload_template_s3()
    
        cf_client.create_stack(
            OnFailure='DELETE',
            **self._get_stack_call_params(True),
        )
    
        self._log_stack_status()

    def release_img(self, component, dm_name):
        tag = self.build_img(component, dm_name)
        _push(tag, dm_name)
        _log.info(f'Pushed {tag}')

    def build_img(self, component, dm_name, *, no_cache=False):
        component = self.Component[component]
        tag = rv.manager.util.get_next_image_tag(self.repo_uri, *component.value)

        build_flags = ' '.join([
            '--no-cache' if no_cache else '',
        ])

        _execute_commands(
            f'docker-machine start {dm_name}',
            f'eval $(docker-machine env {dm_name})',
            f'docker build {build_flags} -f {self.get_dockerfile_path(component)} -t {tag} {self.base_path}'
        )

        _log.info(f'Built {tag}')
        return tag

    @cached_property
    def command_id(self):
        """Id for the currently executing revolio manager command."""
        return str(uuid.uuid4())

    @cached_property
    def _src_path(self):
        return os.path.abspath(os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            '..',  # revolio
            '..',  # src
        ))

    @cached_property
    def repo_uri(self):
        return self.stack_config['Ecr']['Repo']['Url']

    def get_dockerfile_path(self, component):
        a, b = component.value
        return self._get_data_path('dockerfiles', f'Dockerfile-{a}-{b}')

    @cached_property
    def revolio_config(self):
        return self.stack_config['Revolio']

    @cached_property
    def template_key(self):
        return '{service}-template-{timestamp}-{uuid}'.format(
            service=self.SERVICE[1],
            timestamp=dt.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'),
            uuid=uuid.uuid4(),
        )

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
        p = self.stack.get_parameters()
        return p

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
        timestamp = dt.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        tag = uuid.uuid4()
        return f'nudge-change-set-{timestamp}-{tag}'

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
        return os.path.join(self._r_path, 'services', self.SERVICE[0], 'envs', self.env.name.lower(), name)

    def _get_data_path(self, *args):
        return os.path.join(self._src_path, self.SERVICE[0], 'infrastructure', 'data', *args)

    def update_stack(self, change_set):
        self._upload_template_s3()

        if change_set:
            self._change_set_update()
        else:
            self._blind_update()

    def _upload_template_s3(self):
        s3_client.put_object(
            Bucket=self.revolio_config['Bucket'],
            Body=self.stack_template,
            Key=self.template_key,
        )

    def _blind_update(self):
        cf_client.update_stack(
            **self._get_stack_call_params(False),
        )

        prev_event = cf_client.describe_stack_events(StackName=self.stack_name)['StackEvents'][0]['EventId']
        self._log_stack_status(prev_event=prev_event)

    def _change_set_update(self):
        cf_client.create_change_set(
            ChangeSetName=self.stack_change_set_name,
            **self._get_stack_call_params(False),
        )

        _log.info(f'Created change set {ctx.stack_change_set_name}')

        changes = self._get_change_set_changes()
        _log.info(json.dumps(changes, sort_keys=True, indent=4, separators=(',', ': ')))

        if self._prompt_user('update'):
            prev_event = cf_client.describe_stack_events(StackName=self.stack_name)['StackEvents'][0]['EventId']

            cf_client.execute_change_set(
                ChangeSetName=self.stack_change_set_name,
                StackName=self.stack_name,
            )

            self._log_stack_status(prev_event=prev_event)

    def _get_stack_call_params(self, initial):
        return dict(
            StackName=self.stack_name,
            TemplateURL='https://s3.amazonaws.com/{b}/{k}'.format(
                b=self.revolio_config['Bucket'],
                k=self.template_key,
            ),
            Parameters=[
                {
                    'ParameterKey': k,
                    'ParameterValue': v,
                } if v is not UNCHANGED_PARAM else {
                    'ParameterKey': k,
                    'UsePreviousValue': True,
                }
                for k, v in self.get_stack_parameters(initial).items()
            ],
            Tags=[
                {'Key': k, 'Value': v}
                for k, v in self.stack_tags.items()
            ],
            Capabilities=['CAPABILITY_IAM'],
        )

    def _log_stack_status(self, *, prev_event=None):
        while True:
            time.sleep(5)

            # self.stack.execute_actions()

            new_events = self._get_new_events(self.stack_name, prev_event=prev_event)
            if not new_events:
                continue

            prev_event = new_events[-1]['EventId']
            for e in new_events:
                msg = '{resource} | {status}'.format(
                    resource=e['LogicalResourceId'],
                    status=e['ResourceStatus'],
                )

                reason = e.get('ResourceStatusReason')
                if reason is not None:
                    msg += ' | {}'.format(reason)

                _log.info(msg)

            if self._stack_is_stable(self.stack_name):
                break

    def _stack_is_stable(self, stack_name):
        status = cf_client.describe_stacks(StackName=stack_name)['Stacks'][0]['StackStatus']
        return status in ['UPDATE_COMPLETE', 'ROLLBACK_COMPLETE', 'UPDATE_ROLLBACK_COMPLETE']

    def _get_new_events(self, stack_name, *, prev_event=None):
        return list(reversed(list(itertools.takewhile(
            lambda e: e['EventId'] != prev_event,
            itertools.chain.from_iterable(map(
                lambda r: r['StackEvents'],
                cf_client.get_paginator('describe_stack_events').paginate(StackName=stack_name))
            )
        ))))

    def _prompt_user(self, action=None):
        while True:
            key = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))

            msg = f'Type "{key}" to confirm'
            if action is not None:
                msg = ' '.join([msg, action])

            value = click.prompt(msg, type=str)
            
            if value == key:
                return True
            elif value == '':
                return False

            _log.warning('Invalid confirmation value')

    def _get_change_set_changes(self):
        while True:
            r = cf_client.describe_change_set(
                ChangeSetName=self.stack_change_set_name,
                StackName=self.stack_name,
            )
            status = r['Status']
            if status != 'CREATE_COMPLETE':
                _log.info(f'Change set status: {status}')
                time.sleep(5)
                continue

            break

        changes = r['Changes']
        while 'NextToken' in r:
            r = cf_client.describe_change_set(
                ChangeSetName=self.stack_change_set_name,
                StackName=self.stack_name,
                NextToken=r['NextToken'],
            )
            changes.extend(r['Changes'])

        return changes


def _generate_db_password():
    char_set = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return ''.join(random.SystemRandom().choice(char_set) for _ in range(32))


def _push(tag, dm_name):
    repo_account_id = tag.split('.', 1)[0]
    username, password, registry = _get_ecr_credentials(repo_account_id)
    _execute_commands(
        f'docker-machine start {dm_name}',
        f'eval $(docker-machine env {dm_name})',
        f'docker login -u {username} -p {password} {registry}',
        f'docker push {tag}',
    )


def _get_ecr_credentials(repo_account_id):
    ecr_client = boto3.client('ecr')  # _get_ecr_client()
    response = ecr_client.get_authorization_token(
        registryIds=[repo_account_id],
    )
    auth_data = response['authorizationData'][0]

    token = base64.b64decode(auth_data['authorizationToken']).decode("utf-8")
    username, password = token.split(':')
    endpoint = auth_data['proxyEndpoint'][len('https://'):]
    return username, password, endpoint


def _execute_commands(*commands):
    command = '; '.join(commands)
    _log.info(command)

    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
    )

    while True:
        status = proc.stdout.readline().decode('utf-8').rstrip('\n')
        if not status:
            break

        _log.info(status)
