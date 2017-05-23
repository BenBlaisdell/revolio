import awacs.aws
import awacs.kms
import troposphere as ts
import troposphere.s3
import troposphere.kms


def add_resources(t, config):
    t.add_resource(ts.s3.Bucket(
        'Bucket',
        BucketName=config['BucketName'],
    ))

    key = t.add_resource(ts.kms.Key(
        'SecretsKey',
        KeyPolicy=awacs.aws.Policy(
            Statement=[awacs.aws.Statement(
                Principal=awacs.aws.AWSPrincipal(config['KeyAdmins']),
                Effect='Allow',
                Action=[awacs.kms.Action('*')],
                Resource=['*'],
            )],
        ),
    ))

    t.add_resource(ts.kms.Alias(
        'SecretsKeyAlias',
        AliasName='alias/{}'.format(config['KeyName']),
        TargetKeyId=ts.Ref(key),
    ))
