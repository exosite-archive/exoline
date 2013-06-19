#!/usr/bin/env python

from setuptools import setup
from exoline import __version__ as version

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup (name='exoline',
       version=version,
       url = 'http://github.com/dweaver/exoline',
       author = 'Dan Weaver',
       author_email = 'danweaver@exosite.com',
       description = 'Command line interface for Exosite platform.',
       packages=['exoline'],
       dependency_links=['https://github.com/dweaver/pyonep/tarball/master#egg=onepv1lib-0.3'],
       install_requires=required,
       )
