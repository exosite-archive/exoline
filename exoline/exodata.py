#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Exosite Data API Command Line Interface
   Provides access to the HTTP Data Interface API:
   http://developers.exosite.com/display/OP/HTTP+Data+Interface+API

Usage:
    exodata read [options] <cik> <alias> ... 
    exodata write [options] <cik> <alias>=<value> ...
    exodata ip [options]

Options:
    -h --help     Show this screen
    -v --version  Show version
    --url=<url>   One Platform URL [default: http://m2.exosite.com]

"""
# Copyright (c) 2013, Exosite, LLC
# All rights reserved
import sys
import re

import requests
from docopt import docopt
from exoline import __version__

class AppException(Exception):
    pass


class ExoData():
    def __init__(self, url='http://m2.exosite.com'):
        self.url = url

    def read(self, cik, aliases):
        headers = {'X-Exosite-CIK': cik,
                'Accept': 'application/x-www-form-urlencoded; charset=utf-8'}
        url = self.url + '/onep:v1/stack/alias?' + '&'.join(aliases)
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        return r.text

    def write(self, cik, alias_values):
        headers = {'X-Exosite-CIK': cik,
                'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'}
        url = self.url + '/onep:v1/stack/alias'
        data = '&'.join(['='.join(t) for t in alias_values])
        r = requests.post(url, headers=headers, data=data)
        r.raise_for_status()
        return r.text

    def ip(self): 
        r = requests.get(self.url + '/ip')
        r.raise_for_status()
        return r.text


def handle_args(args):
    ed = ExoData(url=args['--url'])

    if args['read']:
        print(ed.read(args['<cik>'], args['<alias>']))
    elif args['write']:
        alias_values = []
        re_assign = re.compile('(.*)=(.*)')
        for assignment in args['<alias>=<value>']:
            m = re_assign.match(assignment)
            if m is None or len(m.groups()) != 2:
                raise AppException("Bad alias assignment format")
            alias_values.append(m.groups())
        ed.write(args['<cik>'], alias_values)
    elif args['ip']:
        print(ed.ip())


if __name__ == '__main__':
    args = docopt(__doc__, version="Exosite Data API {}".format(__version__))
    try:
        handle_args(args)
    except AppException as ex:
        print(ex)
        sys.exit(1)
