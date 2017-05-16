import json
import datetime as dt
import uuid
import logging
import time
import string
import random

import boto3
import click


_logger = logging.getLogger(__name__)
client = boto3.client('cloudformation')


def update_stack(ctx):

    c_s_name = _get_change_set_name()
    stack_name = ctx.stack_name

    client.create_change_set(
        StackName=stack_name,
        TemplateBody=ctx.web_template,
        ChangeSetName=c_s_name,
        Capabilities=['CAPABILITY_IAM'],
    )

    _logger.info('Created change set {}'.format(c_s_name))

    changes = _get_change_set_changes(c_s_name, stack_name)
    _logger.info(json.dumps(changes, sort_keys=True, indent=4, separators=(',', ': ')))

    if _user_prompted_update():
        client.execute_change_set(
            ChangeSetName=c_s_name,
            StackName=stack_name,
        )


def _user_prompted_update():
    while True:
        key = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))
        value = click.prompt('Type "{}" to confirm update'.format(key), type=str)
        if value == key:
            return True
        elif value == '':
            return False

        _logger.warning('Invalid confirmation value')


def _get_change_set_changes(c_s_name, stack_name):
    while True:
        r = client.describe_change_set(
            ChangeSetName=c_s_name,
            StackName=stack_name,
        )
        status = r['Status']
        if status != 'CREATE_COMPLETE':
            _logger.info('Change set status: {}'.format(status))
            time.sleep(10)
            continue

        break

    changes = r['Changes']
    while 'NextToken' in r:
        r = client.describe_change_set(
            ChangeSetName=c_s_name,
            StackName=stack_name,
            NextToken=r['NextToken'],
        )
        changes.extend(r['Changes'])

    return changes



def _get_change_set_name():
    return 'nudge-{timestamp}-{uuid}'.format(
        timestamp=dt.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'),
        uuid=uuid.uuid4(),
    )
