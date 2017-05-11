# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


setup(
    name='nudge',
    version='1.0.0',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=[
        'cached-property',
        'flask',
        'flask-sqlalchemy',
        'psycopg2',
        'sqlalchemy',
    ],
)
