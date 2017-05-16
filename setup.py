# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


setup(
    name='nudge',
    version='1.0.0',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=[
        'awacs',
        'boto3',
        'cached-property',
        'click',
        'click-log',
        'flask',
        'flask-sqlalchemy',
        'marshmallow',
        'psycopg2',
        'requests',
        'ruamel.yaml',
        'sqlalchemy',
        'troposphere',
    ],
    tests_require=[
        'pytest',
    ],
    entry_points={
        'console_scripts': [
            'nudge = nudge.manager:cli',
        ],
    },
)
