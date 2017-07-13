import collections
import itertools
import os.path
import packaging.version
import re

import boto3
import click
import troposphere as ts
import troposphere.ecs
from flask import json
import ruamel.yaml as ryaml


class EnumType(click.Choice):

    def __init__(self, enum):
        super(EnumType, self).__init__(enum.__members__)
        self._enum = enum

    def convert(self, value, param, ctx):
        if isinstance(value, self._enum):
            return value

        return self._enum[super(EnumType, self).convert(value, param, ctx)]


_ecr_client = boto3.client('ecr')


# https://docs.aws.amazon.com/AmazonECR/latest/APIReference/API_Repository.html
_ecr_re = re.compile(
    r'\A(?P<account>[0-9]{12})'
    r'.dkr.ecr.us-east-1.amazonaws.com/'
    r'(?P<repo>(?:[a-z0-9]+(?:[._-][a-z0-9]+)*/)*[a-z0-9]+(?:[._-][a-z0-9]+)*)'
)


def get_revolio_config():
    with open(os.path.expanduser('~/.revolio/config')) as f:
        return ryaml.load(f, Loader=ryaml.Loader)


def get_next_image_tag(uri, *args):
    m = _ecr_re.match(uri).groupdict()
    tag = _get_next_version_tag(m['account'], m['repo'], *args)
    return f'{uri}:{tag}'


def get_latest_image_tag(uri, *args):
    m = _ecr_re.match(uri).groupdict()
    prefix = '-'.join(args)
    version = _get_latest_version(m['account'], m['repo'], *args)
    return f'{uri}:{prefix}-{version}'


def _get_next_version_tag(reg_id, repo, *args):
    major, minor, build = map(int, _get_latest_version(reg_id, repo, *args).split('.'))
    build += 1

    prefix = '-'.join(args)
    version = '.'.join(map(str, (major, minor, build)))
    return f'{prefix}-{version}'


def _get_latest_version(reg_id, repo, *args):
    tags = map(
        lambda i: i['imageTag'],
        itertools.chain.from_iterable(map(
            lambda r: r['imageIds'],
            _ecr_client.get_paginator('list_images').paginate(
                registryId=reg_id,
                repositoryName=repo,
                filter={'tagStatus': 'TAGGED'},
            ),
        )),
    )

    # get only the desired component tags
    prefix = '{}-'.format('-'.join(args))
    tags = filter(lambda t: t.startswith(prefix), tags)

    versions = map(lambda t: packaging.version.parse(t[len(prefix):]), tags)

    return max(itertools.chain(
        [packaging.version.parse('0.0.0')],  # default if no images yet
        versions,
    )).base_version


def get_bucket(s3_uri):
    assert s3_uri.startswith('s3://')
    return s3_uri[len('s3://'):].split('/', 1)[0]


def aws_logs_config(group, *, region='us-east-1'):
    return ts.ecs.LogConfiguration(
        LogDriver='awslogs',
        Options={
            'awslogs-group': group,
            'awslogs-region': region,
            'awslogs-stream-prefix': 'logs',
        },
    )


def env(prefix, variables):
    return [
        ts.ecs.Environment(Name=n, Value=v)
        for n, v in collections.ChainMap(
            {
                'AWS_DEFAULT_REGION': ts.Ref('AWS::Region'),
            },
            {f'{prefix}_{n}': json.dumps(v) for n, v in variables.items()}
        ).items()
    ]
