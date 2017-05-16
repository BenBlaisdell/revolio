import logging
import os

import click
import click_log

from nudge.manager import commands
from nudge.manager.context import NudgeCommandContext, EnvName, Component
from nudge.manager.util import EnumType


_logger = logging.getLogger(__name__)


@click.group()
@click.argument('resources')
@click.option('--env', '-e', default=EnvName.DEV)
@click_log.simple_verbosity_option()
@click_log.init(__name__)
@click.pass_context
def cli(ctx, resources, env):
    ctx.obj = NudgeCommandContext(
        data_path=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data'),
        resources_path=resources,
        env_name=env,
    )


@cli.command('build-template')
@click.pass_obj
def build_template(cmd_ctx):
    commands.build_template(cmd_ctx)


@cli.command('update-stack')
@click.pass_obj
def update_stack(cmd_ctx):
    commands.build_template(cmd_ctx)
    commands.update_stack(cmd_ctx)


@cli.command('release')
@click.argument('component', type=EnumType(Component))
@click.option('--docker-machine', '-dm', default='default')
@click.pass_obj
def release(cmd_ctx, component, docker_machine):
    commands.release(cmd_ctx, component, docker_machine)


if __name__ == '__main__':
    cli()
