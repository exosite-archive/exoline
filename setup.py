#!/usr/bin/env python

from setuptools import setup
import sys
try:
    import py2exe
except ImportError:
    pass

from glob import glob

from exoline import __version__ as version

with open('requirements.txt') as f:
    required = f.read().splitlines()

import platform
if platform.system() == "Windows":
    data_files = [("Microsoft.VC90.CRT", glob(r'C:\Program Files (x86)\Microsoft Visual Studio 12.0\VC\redist\x86\Microsoft.VC90.CRT\*.*'))]
else:
    data_files = []

try:
    from collections import OrderedDict
except ImportError:
    required.append('ordereddict>=1.1')

try:
    import importlib
except ImportError:
    required.append('importlib>=1.0.2')

if sys.version_info < (3, 0):
    required.append('unicodecsv==0.9.4')

if sys.version_info < (2, 7, 9):
    # https://urllib3.readthedocs.org/en/latest/security.html#insecureplatformwarning
    required = required + ['pyopenssl', 'ndg-httpsclient', 'pyasn1']

import os
long_description = open('README.md').read() + '\n\n' + open('HISTORY.md').read()
if os.path.exists('README.txt'):
    # read rst version if it exists
    # (usually because register.py was run)
    long_description = open('README.txt').read()

setup(
    name='exoline',
    version=version,
    url = 'http://github.com/exosite/exoline',
    author = 'Dan Weaver',
    author_email = 'danweaver@exosite.com',
    description = 'Command line interface for Exosite platform.',
    long_description = long_description,
    packages=['exoline', 'exoline.plugins'],
    package_dir={'exoline': 'exoline', 'plugins': 'exoline/plugins'},
    scripts=['bin/exo', 'bin/exoline'],
    keywords=['exosite', 'onep', 'one platform', 'm2m', 'iot', 'cli'],
    install_requires=required,
    zip_safe=False,
    #always_unzip=True,
	console=['exoline/exo.py'],
    data_files=data_files,
	options={
		'py2exe':
		{
			'includes': ['yaml', 'exoline']
		}
	}
    )

