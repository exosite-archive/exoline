#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Exosite RPC API Command Line Interface
   Provides command line access to the Remote Procedure Call API:
   http://developers.exosite.com/display/OP/Remote+Procedure+Call+API

Usage:
  exo [options] read [--follow] [--limit=<limit>] [--selection=all|autowindow|givenwindow] <cik> <rid>
  exo [options] write <cik> <rid> --value=<value>
  exo [options] record <cik> <rid> --value=<timestamp,value> ...
  exo [options] create-dataport <cik> (--format=binary|boolean|float|integer|string) [--name=<name>]
  exo [options] create-client <cik> [--name=<name>]
  exo [options] map <cik> <rid> <alias>
  exo [options] unmap <cik> <alias>
  exo [options] drop <cik> <rid> ...
  exo [options] listing [--plain] <cik> (--type=client|dataport|datarule|dispatch) ...
  exo [options] info <cik> <rid> [--cikonly] 
  exo [options] flush <cik> <rid>
  exo [options] tree <cik> [--verbose]
  exo [options] lookup-rid <cik> <cik-to-find>
  exo [options] drop-all-children <cik>

Options:
  --host=<host>        OneP URL. Default is $EXO_HOST or m2.exosite.com.
  --httptimeout=<sec>  HTTP timeout setting.
  --pretty             Pretty print output
  -h --help            Show this screen.
  -v --version         Show version.

"""
# Copyright (c) 2013, Exosite, LLC
# All rights reserved
import sys
import os
import json
import csv
import re
from datetime import datetime
import time
from pprint import pprint
from collections import OrderedDict

from docopt import docopt
from onepv1lib import onep
from onepv1lib import onep_exceptions
from exoline import __version__

DEFAULT_HOST='m2.exosite.com'

class AppException(Exception):
    pass


class ExoRPC():
    '''Wrapper for onepv1lib RPC API. Raises exceptions on error and provides some reasonable defaults.'''
    def __init__(self, 
            host='http://' + DEFAULT_HOST, 
            httptimeout=60, 
            verbose=False):
        self.exo = onep.OnepV1(host=host, httptimeout=httptimeout)       

    def _raise_for_response(self, isok, response):
        if not isok:
            raise AppException(response)

    def read(self, cik, rid, limit, sort='asc', starttime=None, selection='all'):
        options = {'limit': limit,
               'sort': sort,
               'selection': selection}
        if starttime is not None:
            options['starttime'] = starttime
        isok, response = self.exo.read(
            cik,
            rid,
            options)
        self._raise_for_response(isok, response)
        return response

    def write(self, cik, rid, values):
        for v in values:
            self.exo.write(cik, rid, v, {}, defer=True)

        if self.exo.has_deferred(cik):
            responses = self.exo.send_deferred(cik)
            for call, isok, response in responses:
                self._raise_for_response(isok, response)

    def record(self, cik, rid, entries):
        isok, response = self.exo.record(cik, rid, entries, {})
        self._raise_for_response(isok, response)

    def create(self, cik, type, desc):
        return self.exo.create(cik, type, desc)

    def create_dataport(self, cik, format, name=None):
        desc = {'format': format,
                'retention': {
                    'count': 'infinity',
                    'duration': 'infinity'}
                }
        if name is not None:
            desc['name'] = name

        isok, response = self.create(cik, 'dataport', desc)
        self._raise_for_response(isok, response)
        return response 

    def create_client(self, cik, name=None, desc=None):
        if desc is None:
            # default description
            desc = {'limits': {'dataport': 'inherit',
                                'datarule': 'inherit',
                                'dispatch': 'inherit',
                                'disk': 'inherit',
                                'io': 'inherit'},
                    'writeinterval': 'inherit'}
        if name is not None:
            desc['name'] = name

        isok, response = self.create(cik, 'client', desc)
        self._raise_for_response(isok, response)
        return response

    def drop(self, cik, rids):
        for rid in rids:
            self.exo.drop(cik, rid, defer=True)

        if self.exo.has_deferred(cik):
            responses = self.exo.send_deferred(cik)
            for call, isok, response in responses:
                self._raise_for_response(isok, response)

    def map(self, cik, rid, alias):
        isok, response = self.exo.map(cik, rid, alias)
        self._raise_for_response(isok, response)
        return response
    
    def unmap(self, cik, alias):
        isok, response = self.exo.unmap(cik, alias)
        self._raise_for_response(isok, response)
        return response

    def listing(self, cik, types):
        isok, response = self.exo.listing(cik, types)
        self._raise_for_response(isok, response)
        return response

    def info(self, cik, rid, options={}, cikonly=False):
        isok, response = self.exo.info(cik, rid, options)
        self._raise_for_response(isok, response)
        if cikonly:
            if not response.has_key('key'):
                raise AppException('{} has no CIK'.format(rid))
            return response['key'] 
        else:
            return response

    def flush(self, cik, rids):
        for rid in rids:
            self.exo.flush(cik, rid, defer=True)

        if self.exo.has_deferred(cik):
            responses = self.exo.send_deferred(cik)
            for call, isok, response in responses:
                self._raise_for_response(isok, response)

    def _print_node(self, rid, info, aliases, cli_args, spacer, islast):
        typ = info['basic']['type']
        id = 'cik: ' + info['key'] if typ=='client' else 'rid: ' + rid
        name = info['description']['name']
        try:
            # Units are a portals only thing
            # u'comments': [[u'public', u'{"unit":"Fahrenheit"}']],']]
            units = json.loads(info['comments'][0][1])['unit']
            if len(units.strip()) == 0:
                units = 'none'
        except:
            units = 'none'

        # Sometimes aliases is a dict, sometimes a list. TODO: Why?
        # Translate it into a list. 
        if type(aliases) is dict:
            aliases = aliases.get(rid, [])
        elif aliases is None:
            aliases = []

        opt = OrderedDict()
        def add_opt(o, label, value):
            if o is True or (cli_args.has_key(o) and cli_args[o] == True):
                opt[label] = value
        add_opt(True, 'type', typ)
        if info['description'].has_key('format'):
            add_opt(True, 'format', info['description']['format'])
        add_opt(True, 'name', name)
        add_opt(True, 'aliases', 'none' if len(aliases) == 0 else ', '.join(aliases))
        add_opt('--verbose', 'unit', units)
        add_opt('--verbose', 'rid', rid)
        
        print('{}{} {}'.format(
            spacer,
            id,
            '' if len(opt) == 0 else '({})'.format(', '.join(
                ['{}: {}'.format(k, v) for k, v in opt.iteritems()]))))

    def tree(self, cik, aliases=None, cli_args={}, spacer=''): 
        '''Print a tree of entities in OneP'''
        types = ['dataport', 'datarule', 'dispatch', 'client']
        isok, response = self.exo.listing(cik, types=types)
        self._raise_for_response(isok, response)
        listing = response
        
        # print root node
        if len(spacer) == 0:
            print(cik)

        # print everything
        for t_idx, t in enumerate(types):
            typelisting = listing[t_idx]
            islast_nonempty = (t_idx == len(types) - 1) or (all(len(x) == 0 for x in listing[t_idx + 1:]))
            for rid_idx, rid in enumerate(typelisting):
                isok, response = self.exo.info(cik, rid)
                self._raise_for_response(isok, response)
                info = response
                islastoftype = rid_idx == len(typelisting) - 1
                islast = islast_nonempty and islastoftype
                new_spacer = spacer + '  ' # TODO: fancy piping with '│ ' 
                indent_spacer = '└──' if islast else '├──'
                if t == 'client':
                    next_cik = info['key']
                    self._print_node(rid, info, aliases, cli_args, new_spacer + indent_spacer, islast)
                    self.tree(next_cik, info['aliases'], cli_args, new_spacer)
                else:
                    self._print_node(rid, info, aliases, cli_args, new_spacer + indent_spacer, islast)
                   
    def drop_all_children(self, cik):
        isok, listing = self.exo.listing(cik, types=['client', 'dataport', 'datarule', 'dispatch'])
        self._raise_for_response(isok, listing)

        for l in listing:
            self.drop(cik, l)

    def lookup_rid(self, cik, cik_to_find):
        isok, listing = self.exo.listing(cik, types=['client'])
        self._raise_for_response(isok, listing)

        for rid in listing[0]:
            self.exo.info(cik, rid, defer=True)

        if self.exo.has_deferred(cik):
            responses = self.exo.send_deferred(cik)
            for idx, r in enumerate(responses):
                call, isok, response = r
                self._raise_for_response(isok, response)

                if response['key'] == cik_to_find:
                    return listing[0][idx]

       

def plain_print(arg):
    print(arg)

def handle_args(args):
    er = ExoRPC(host=args['--host'])
    cik = args['<cik>']
    if args['--pretty']:
        pr = pprint
    else:
        pr = plain_print
    if args['read']:
        rid = args['<rid>'][0]
        limit = args['--limit']
        limit = 1 if limit is None else int(limit)
        dr = csv.DictWriter(sys.stdout, ['timestamp', 'value'])
        def printline(timestamp, val):
            dt = datetime.fromtimestamp(timestamp)
            dr.writerow({'timestamp': str(dt), 'value': val})
        
        if args['--follow']:
            results = er.read(cik, 
                              rid, 
                              limit=1,
                              sort='desc')
            last_t, last_v = results[-1]
            printline(last_t, last_v)

            while True:
                results = er.read(cik, 
                                  rid,
                                  limit=10000,
                                  starttime=last_t + 1)

                for t, v in results:
                    printline(t, v)

                if len(results) > 0:
                    last_t, last_v = results[-1]

                time.sleep(2)
        else:
            for t, v in er.read(cik,
                                rid,
                                limit=limit):
                printline(t, v)
    elif args['write']:
        er.write(cik, args['<rid>'][0], args['--value'])
    elif args['record']:
        entries = []
        # split timestamp, value
        reentry = re.compile('(-?\d+),(.*)')
        for v in args['--value']:
            match = reentry.match(v)    
            g = match.groups()
            entries.append([int(g[0]), g[1]])
        er.record(cik, args['<rid>'][0], entries)
    elif args['create-dataport']:
        pr(er.create_dataport(cik, args['--format'], name=args['--name']))
    elif args['create-client']:
        pr(er.create_client(cik, name=args['--name']))
    elif args['map']:
        er.map(cik, args['<rid>'][0], args['<alias>'])
    elif args['unmap']:
        er.unmap(cik, args['<alias>'])
    elif args['drop']:
        er.drop(cik, args['<rid>'])
    elif args['listing']:
        types = args['--type']
        listing = er.listing(cik, types)
        if args['--plain'] == True:
            if len(types) != 1:
                raise AppException("--plain not valid with more than one type")
            for cik in listing[0]:
                print(cik)
        else:
            pr(listing)
    elif args['info']:
        pr(er.info(cik, args['<rid>'][0], cikonly=args['--cikonly']))
    elif args['flush']:
        er.flush(cik, args['<rid>'])
    # special commands
    elif args['tree']:
        er.tree(cik, cli_args=args)
    elif args['lookup-rid']:
        rid = er.lookup_rid(cik, args['<cik-to-find>'])
        if rid is not None:
            pr(rid)
    elif args['drop-all-children']:
        er.drop_all_children(cik)


if __name__ == '__main__':
    args = docopt(__doc__, version="Exosite Data API {}".format(__version__))

    # substitute environment variables
    if args['--host'] is None:
        args['--host'] = os.environ.get('EXO_HOST', DEFAULT_HOST)

    try:
        handle_args(args)
    except AppException as ex:
        print("AppException: {}".format(ex))
        sys.exit(1)
    except onep_exceptions.OnePlatformException as ex:
        print("OnePlatformException: {}".format(ex))
        sys.exit(1)
