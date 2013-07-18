#!/usr/bin/env python

from setuptools import setup
from exoline import __version__ as version

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='exoline',
    version=version,
    url = 'http://github.com/dweaver/exoline',
    author = 'Dan Weaver',
    author_email = 'danweaver@exosite.com',
    description = 'Command line interface for Exosite platform.',
    long_description = open('README.md').read() + '\n\n' +
                      open('HISTORY.md').read(),
    packages=['exoline'],
    package_dir={'exoline': 'exoline'},
    scripts=['bin/exo', 'bin/exoline', 'bin/exodata'],
    keywords=['exosite', 'onep', 'one platform', 'm2m'],
    install_requires=required,
    zip_safe=False,
    )
