# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


setup(
    name='nudge',
    version='1.0.0',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=[
        'boto3',
        'cached-property',
        'flask',
        'flask-sqlalchemy',
        'marshmallow',
        'psycopg2',
        'ruamel.yaml',
        'sqlalchemy',
    ],
)
