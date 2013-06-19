#!/usr/bin/env python

from setuptools import setup
from exoline import __version__ as version

requires = []

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
    keywords=['exosite', 'onep', 'one platform', 'm2m'],
    dependency_links=['https://github.com/dweaver/pyonep/tarball/master#egg=onepv1lib-0.3'],
    install_requires=requires,
    zip_safe=False,
    )
