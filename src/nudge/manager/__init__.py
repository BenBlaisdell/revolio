import logging
import os
import random
import string

import boto3
import botocore.client
import click
import click_log

from nudge.manager import commands
from nudge.manager.context import NudgeCommandContext, EnvName, Component
from nudge.manager.util import EnumType


_logger = logging.getLogger(__name__)


@click.group()
@click.argument('resources')
@click.option('--env', '-e', default=EnvName.DEV, type=EnumType(EnvName))
@click_log.simple_verbosity_option()
@click_log.init(__name__)
@click.pass_context
def cli(ctx, resources, env):
    ctx.obj = NudgeCommandContext(
        data_path=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data'),
        resources_path=resources,
        env_name=env,
    )


# cloudformation


@cli.command('build-template')
@click.pass_obj
def build_template(cmd_ctx):
    commands.build_template(cmd_ctx)


@cli.command('create-stack')
@click.pass_obj
def update_stack(cmd_ctx):
    commands.build_template(cmd_ctx)
    commands.create_stack(cmd_ctx)


@cli.command('update-stack')
@click.pass_obj
def update_stack(cmd_ctx):
    commands.build_template(cmd_ctx)
    commands.update_stack(cmd_ctx)


# docker


@cli.command('release-img')
@click.argument('component', type=EnumType(Component))
@click.option('--docker-machine', '-dm', default='default')
@click.pass_obj
def release_img(cmd_ctx, component, docker_machine):
    commands.release_img(cmd_ctx, component, docker_machine)


@cli.command('build-img')
@click.argument('component', type=EnumType(Component))
@click.option('--docker-machine', '-dm', default='default')
@click.option('--no-cache', is_flag=True)
@click.pass_obj
def build_img(cmd_ctx, component, docker_machine, no_cache):
    commands.build_img(cmd_ctx, component, docker_machine, no_cache=no_cache)


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
    _logger.info(''.join(random.choice(options) for _ in range(12)))

if __name__ == '__main__':
    cli()
