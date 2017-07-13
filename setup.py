# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


setup(
    name='revolio',
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
        'packaging',
        'psycopg2',
        'python-box',
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
            'revolio = revolio.manager.cli:cli',
        ],
    },
)
