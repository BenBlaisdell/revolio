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

from nudge.manager.context import UNCHANGED_PARAM
from nudge.manager.infrastructure.env import EnvResources


_log = logging.getLogger(__name__)


cf_client = boto3.client('cloudformation')
s3_client = boto3.client('s3')


def build_template(ctx):
    ctx.save_template(ctx.stack.get_template())


def create_stack(ctx):
    _upload_template_s3(ctx)

    cf_client.create_stack(
        OnFailure='DELETE',
        **_get_stack_call_params(ctx, True),
    )

    _log_stack_status(ctx)


def update_stack(ctx, change_set):
    _upload_template_s3(ctx)

    if change_set:
        _change_set_update(ctx)
    else:
        _blind_update(ctx)


def _upload_template_s3(ctx):
    s3_client.put_object(
        Bucket=ctx.revolio_config['Bucket'],
        Body=ctx.stack_template,
        Key=ctx.template_key,
    )


def _blind_update(ctx):
    cf_client.update_stack(
        **_get_stack_call_params(ctx, False),
    )

    prev_event = cf_client.describe_stack_events(StackName=ctx.stack_name)['StackEvents'][0]['EventId']
    _log_stack_status(ctx, prev_event=prev_event)


def _change_set_update(ctx):
    cf_client.create_change_set(
        ChangeSetName=ctx.stack_change_set_name,
        **_get_stack_call_params(ctx, False),
    )

    _log.info('Created change set {}'.format(ctx.stack_change_set_name))

    changes = _get_change_set_changes(ctx)
    _log.info(json.dumps(changes, sort_keys=True, indent=4, separators=(',', ': ')))

    if _user_prompted_update():
        prev_event = cf_client.describe_stack_events(StackName=ctx.stack_name)['StackEvents'][0]['EventId']

        cf_client.execute_change_set(
            ChangeSetName=ctx.stack_change_set_name,
            StackName=ctx.stack_name,
        )

        _log_stack_status(ctx, prev_event=prev_event)


def _get_stack_call_params(ctx, initial):
    return dict(
        StackName=ctx.stack_name,
        TemplateURL='https://s3.amazonaws.com/{b}/{k}'.format(
            b=ctx.revolio_config['Bucket'],
            k=ctx.template_key,
        ),
        Parameters=[
            {
                'ParameterKey': k,
                'ParameterValue': v,
            } if v is not UNCHANGED_PARAM else {
                'ParameterKey': k,
                'UsePreviousValue': True,
            }
            for k, v in ctx.get_stack_parameters(initial).items()
        ],
        Tags=[
            {'Key': k, 'Value': v}
            for k, v in ctx.stack_tags.items()
        ],
        Capabilities=['CAPABILITY_IAM'],
    )


def _log_stack_status(ctx, *, prev_event=None):
    while True:
        time.sleep(5)

        ctx.stack.execute_actions()

        new_events = _get_new_events(ctx.stack_name, prev_event=prev_event)
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

        if _stack_is_stable(ctx.stack_name):
            break


def _stack_is_stable(stack_name):
    status = cf_client.describe_stacks(StackName=stack_name)['Stacks'][0]['StackStatus']
    return status in ['UPDATE_COMPLETE', 'ROLLBACK_COMPLETE', 'UPDATE_ROLLBACK_COMPLETE']


def _get_new_events(stack_name, *, prev_event=None):
    return list(reversed(list(itertools.takewhile(
        lambda e: e['EventId'] != prev_event,
        itertools.chain.from_iterable(map(
            lambda r: r['StackEvents'],
            cf_client.get_paginator('describe_stack_events').paginate(StackName=stack_name))
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

        _log.warning('Invalid confirmation value')


def _get_change_set_changes(ctx):
    while True:
        r = cf_client.describe_change_set(
            ChangeSetName=ctx.stack_change_set_name,
            StackName=ctx.stack_name,
        )
        status = r['Status']
        if status != 'CREATE_COMPLETE':
            _log.info('Change set status: {}'.format(status))
            time.sleep(5)
            continue

        break

    changes = r['Changes']
    while 'NextToken' in r:
        r = cf_client.describe_change_set(
            ChangeSetName=ctx.stack_change_set_name,
            StackName=ctx.stack_name,
            NextToken=r['NextToken'],
        )
        changes.extend(r['Changes'])

    return changes
