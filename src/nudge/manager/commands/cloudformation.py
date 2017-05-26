import datetime as dt
import itertools
import json
import logging
import random
import string
import time
import uuid

import boto3
import click

from nudge.manager import stacks
from nudge.manager.context import Stack


_logger = logging.getLogger(__name__)


client = boto3.client('cloudformation')


def build_template(ctx, s):
    config = ctx.get_architecture_config(s)
    r_group = _get_resource_group(s)(config)
    ctx.save_template(s, r_group.get_template())


_resource_groups = {
    Stack.WEB: stacks.web.WebResources,
    Stack.REPO: stacks.repo.RepoResources,
    Stack.S3: stacks.s3.S3Resources,
    Stack.DB: stacks.db.DatabaseResources,
    Stack.WORKER: stacks.worker.WorkerResources,
}


def _get_resource_group(s):
    if s not in _resource_groups:
        raise Exception('No builder for stack type: {}'.format(s))

    return _resource_groups[s]


def create_stack(ctx, stack_type):
    stack_name = ctx.get_stack_name(stack_type)
    client.create_stack(
        OnFailure='DELETE',
        **_get_stack_call_params(ctx, stack_name, stack_type),
    )


def update_stack(ctx, stack_type):

    c_s_name = _get_change_set_name(stack_type)
    stack_name = ctx.get_stack_name(stack_type)

    client.create_change_set(
        ChangeSetName=c_s_name,
        **_get_stack_call_params(ctx, stack_name, stack_type),
    )

    _logger.info('Created change set {}'.format(c_s_name))

    changes = _get_change_set_changes(c_s_name, stack_name)
    _logger.info(json.dumps(changes, sort_keys=True, indent=4, separators=(',', ': ')))

    if _user_prompted_update():
        _update_stack(c_s_name, stack_name)


def _get_stack_call_params(ctx, s_name, s_type):
    return dict(
        StackName=s_name,
        TemplateBody=ctx.get_template(s_type),
        Tags=[
            {'Key': k, 'Value': v}
            for k, v in ctx.get_stack_tags(s_type)
        ],
        Capabilities=['CAPABILITY_IAM'],
    )


def _update_stack(c_s_name, stack_name):
    prev_event = client.describe_stack_events(StackName=stack_name)['StackEvents'][0]['EventId']

    client.execute_change_set(
        ChangeSetName=c_s_name,
        StackName=stack_name,
    )

    while True:
        time.sleep(5)
        new_events = _get_new_events(stack_name, prev_event)
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

            _logger.info(msg)

        if _stack_is_stable(stack_name):
            break


def _stack_is_stable(stack_name):
    status = client.describe_stacks(StackName=stack_name)['Stacks'][0]['StackStatus']
    return status in ['UPDATE_COMPLETE', 'ROLLBACK_COMPLETE']


def _get_new_events(stack_name, prev_event):
    return list(reversed(list(itertools.takewhile(
        lambda e: e['EventId'] != prev_event,
        itertools.chain.from_iterable(map(
            lambda r: r['StackEvents'],
            client.get_paginator('describe_stack_events').paginate(StackName=stack_name))
        )
    ))))


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
            time.sleep(5)
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


def _get_change_set_name(stack_type):
    return 'nudge-{stack}-change-set-{timestamp}-{uuid}'.format(
        stack=stack_type.value,
        timestamp=dt.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'),
        uuid=uuid.uuid4(),
    )
