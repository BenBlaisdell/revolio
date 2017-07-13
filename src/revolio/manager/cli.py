import logging
import os
import random
import string

import boto3
import botocore.client
import click
import click_log

from revolio.manager.context import _directory
from revolio.manager.util import EnumType, get_revolio_config

# import to register command contexts
import iris.infrastructure
import nudge.infrastructure


_log = logging.getLogger(__name__)


RESOURCES_ENV_VAR = 'REVOLIO_RESOURCES'


@click.group()
@click.option(
    '--resources', '-r',
    type=click.Path(file_okay=False),
    envvar=RESOURCES_ENV_VAR,
    default=lambda: get_revolio_config()['Resources'],
)
@click.option('--env', '-e', type=click.STRING)
@click.argument('service', type=click.STRING)
@click_log.simple_verbosity_option()
@click_log.init('revolio')
@click.pass_context
def cli(ctx, resources, env, service):
    ctx.obj = _directory[service][env](
        resources_path=resources,
    )


# cloudformation


@cli.command('build-template')
@click.pass_obj
def build_template(cmd_ctx):
    cmd_ctx.build_template()


@cli.command('create-stack')
@click.pass_obj
def create_stack(cmd_ctx):
    cmd_ctx.create_stack()


@cli.command('update-stack')
@click.option('--blind', '-b', is_flag=True)
@click.pass_obj
def update_stack(cmd_ctx, blind):
    cmd_ctx.build_template()
    cmd_ctx.update_stack(change_set=(not blind))


@cli.command('build-ecr')
@click.pass_obj
def build_ecr(cmd_ctx):
    _log.info(cmd_ctx.ecr_stack.get_template())


# docker


@cli.command('release-img')
@click.argument('component', type=click.STRING)
@click.option('--docker-machine', '-dm', default='default')
@click.pass_obj
def release_img(cmd_ctx, component, docker_machine):
    cmd_ctx.release_img(component, docker_machine)


@cli.command('build-img')
@click.argument('component', type=click.STRING)
@click.option('--docker-machine', '-dm', default='default')
@click.option('--no-cache', is_flag=True)
@click.pass_obj
def build_img(cmd_ctx, component, docker_machine, no_cache):
    cmd_ctx.build_img(component, docker_machine, no_cache=no_cache)


# config


@cli.command('upload-config')
@click.pass_obj
def upload_config(cmd_ctx):
    boto3.client(
        service_name='s3',
        config=botocore.client.Config(signature_version='s3v4'),
    ).put_object(
        Bucket=cmd_ctx.stack_config['Secrets']['BucketName'],
        Key=cmd_ctx.stack_config['Secrets']['ConfigKey'],
        Body=cmd_ctx.raw_stack_config,
        ServerSideEncryption='aws:kms',
        SSEKMSKeyId='alias/{}'.format(cmd_ctx.stack_config['Secrets']['KeyName']),
    )


@cli.command('gen-id')
@click.option('--upper', '-u', is_flag=True)
def gen_id(upper):
    options = (string.ascii_uppercase if upper else string.ascii_lowercase) + string.digits
    _log.info(''.join(random.choice(options) for _ in range(12)))


# tables

# @cli.command('recreate-tables')
# @click.pass_obj
# def recreate_tables(cmd_ctx):
#     ctx = nudge.core.context.NudgeCoreContext()
#     with ctx.app.flask_app.app_context():
#         ctx.db.recreate_tables()


if __name__ == '__main__':
    cli()
