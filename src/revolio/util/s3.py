def uri(bucket, *paths):
    key = '/'.join(paths)
    return f's3://{bucket}/{key}'
