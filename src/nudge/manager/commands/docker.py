import base64
import logging
import subprocess

import boto3
import nudge.manager.util

_log = logging.getLogger(__name__)


def release_img(ctx, component, dm_name):
    tag = build_img(ctx, component, dm_name)
    _push(tag)
    _log.info('Pushed {}'.format(tag))


def build_img(ctx, component, dm_name, *, no_cache=False):
    tag = nudge.manager.util.get_next_image_tag(ctx.repo_uri, *component.value)

    _execute_commands(
        'eval $(docker-machine env {})'.format(dm_name),
        'docker build {flags} -f {f} -t {t} {p}'.format(
            flags=' '.join([
                '--no-cache' if no_cache else '',
            ]),
            f=ctx.get_dockerfile_path(component),
            t=tag,
            p=ctx.base_path,
        ),
    )

    _log.info('Built {}'.format(tag))

    return tag


def _push(tag):
    repo_account_id = tag.split('.', 1)[0]
    username, password, registry = _get_ecr_credentials(repo_account_id)

    _execute_commands(
        'docker login -u {} -p {} {}'.format(username, password, registry),
        'docker push {}'.format(tag),
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
        status = proc.stdout.readline().decode("utf-8").rstrip('\n')
        if not status:
            break

        _log.info(status)
