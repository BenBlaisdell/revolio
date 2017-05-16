import logging
import os

import awacs.aws
import awacs.autoscaling
import awacs.events
import awacs.elasticloadbalancing
import awacs.ec2
import awacs.helpers.trust
import marshmallow as mm
import troposphere as ts
import troposphere.cloudwatch
import troposphere.autoscaling
import troposphere.ec2
import troposphere.ecs
import troposphere.iam
import troposphere.logs
import troposphere.elasticloadbalancing
import troposphere.route53

import revolio as rv
import revolio.stack

_logger = logging.getLogger(__name__)


class RepoStackConfigSchema(rv.stack.StackConfigSchema):
    log_group_name = mm.fields.Str()


@rv.stack.stack(RepoStackConfigSchema)
def build_core_template(t, config):
    l_group = t.add_resource(ts.logs.LogGroup(
        'LogGroup',
        LogGroupName='dwh-nudge',
        RetentionInDays=14,
    ))

    cluster = t.add_resource(ts.ecs.Cluster(
        'EcsCluster',
        ClusterName='nudge',
    ))
