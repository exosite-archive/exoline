#!/usr/bin/env python

from setuptools import setup
from exoline import __version__ as version

with open('requirements.txt') as f:
    required = f.read().splitlines()

try:
    from collections import OrderedDict
except ImportError:
    required.append('ordereddict>=1.1')

try:
    import importlib
except ImportError:
    required.append('importlib>=1.0.2')

setup(
    name='exoline',
    version=version,
    url = 'http://github.com/exosite/exoline',
    author = 'Dan Weaver',
    author_email = 'danweaver@exosite.com',
    description = 'Command line interface for Exosite platform.',
    long_description = open('README.md').read() + '\n\n' +
                      open('HISTORY.md').read(),
    packages=['exoline', 'exoline.plugins'],
    package_dir={'exoline': 'exoline', 'plugins': 'exoline/plugins'},
    scripts=['bin/exo', 'bin/exoline'],
    keywords=['exosite', 'onep', 'one platform', 'm2m'],
    install_requires=required,
    zip_safe=False,
    )
