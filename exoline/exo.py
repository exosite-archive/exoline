#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Exosite RPC API Command Line Interface
   Provides command line access to the Remote Procedure Call API:
   http://developers.exosite.com/display/OP/Remote+Procedure+Call+API

Usage:
  exo [options] read <cik> <rid> [--follow] [--limit=<limit>] [--selection=all|autowindow|givenwindow] 
  exo [options] write <cik> <rid> --value=<value>
  exo [options] record <cik> <rid> ((--value=<timestamp,value> ...) | -)
  exo [options] create <cik> (--type=client|clone|dataport|datarule|dispatch) -
  exo [options] create-dataport <cik> (--format=binary|boolean|float|integer|string) [--name=<name>]
  exo [options] create-client <cik> [--name=<name>]
  exo [options] map <cik> <rid> <alias>
  exo [options] unmap <cik> <alias>
  exo [options] lookup <cik> <alias>
  exo [options] drop <cik> <rid> ...
  exo [options] listing [--plain] <cik> (--type=client|dataport|datarule|dispatch) ...
  exo [options] info <cik> <rid> [--cikonly] 
  exo [options] flush <cik> <rid>
  exo [options] tree <cik> [--verbose] [--hide-keys]
  exo [options] lookup-rid <cik> <cik-to-find>
  exo [options] drop-all-children <cik>
  exo [options] record-backdate <cik> <rid> --interval=<seconds> ((--value=<value> ...) | -)
  exo [options] upload <cik> <script-file> [--name=<name>]

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

class ExoException(Exception):
    pass

class RPCException(Exception):
    pass

class ExoRPC():
    '''Wrapper for onepv1lib RPC API. Raises exceptions on error and provides some reasonable defaults.'''
    def __init__(self, 
            host='http://' + DEFAULT_HOST, 
            httptimeout=60, 
            verbose=True):
        self.exo = onep.OnepV1(host=host, httptimeout=httptimeout)       

    def _raise_for_response(self, isok, response):
        if not isok:
            raise RPCException(response)

    def _raise_for_response_record(self, isok, response):
        '''Undocumented RPC behavior-- if record timestamps are invalid, isok is True
           but response is an array of timestamps and error messages.'''
        self._raise_for_response(isok, response)
        if type(response) is list:
            # TODO: does this always indicate an error condition?
            raise RPCException(', '.join(['{}: {}'.format(msg, t) for msg, t in response]))

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
        self._raise_for_response_record(isok, response)

    def create(self, cik, type, desc):
        isok, response = self.exo.create(cik, type, desc)
        self._raise_for_response(isok, response)
        return response

    def create_dataport(self, cik, format, name=None):
        desc = {"format": format,
                "retention": {
                    "count": "infinity",
                    "duration": "infinity"}
                }
        if name is not None:
            desc['name'] = name
        return self.create(cik, 'dataport', desc)

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
        return self.create(cik, 'client', desc)

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

    def lookup(self, cik, alias):
        isok, response = self.exo.lookup(cik, 'alias', alias)
        self._raise_for_response(isok, response)
        return response

    def listing(self, cik, types):
        isok, response = self.exo.listing(cik, types)
        self._raise_for_response(isok, response)
        return response

    def listing_with_info(self, cik, types):
        listing = self.listing(cik, types)
        # listing is a list of lists per type, like: [['<rid0>', '<rid1>'], ['<rid2>'], [], ['<rid3>']] 
        
        # build up a deferred request per element in each sublist
        for type_list in listing:
            for rid in type_list:
                self.exo.info(cik, rid, defer=True)

        if self.exo.has_deferred(cik):
            responses = self.exo.send_deferred(cik)
            for call, isok, response in responses:
                self._raise_for_response(isok, response)

        # From the return values make a list of dicts like this: 
        # [{'<rid0>':<info0>, '<rid1>':<info1>}, {'<rid2>':<info2>}, [], {'<rid3>': <info3>}] 
        # use ordered dicts in case someone cares about order in the output (?)
        response_index = 0
        listing_with_info = []
        for type_list in listing:
            type_response = OrderedDict() 
            for rid in type_list:
                type_response[rid] = responses[response_index][2]
                response_index += 1
            listing_with_info.append(type_response)

        return listing_with_info

    def info(self, cik, rid, options={}, cikonly=False):
        isok, response = self.exo.info(cik, rid, options)
        self._raise_for_response(isok, response)
        if cikonly:
            if not response.has_key('key'):
                raise ExoException('{} has no CIK'.format(rid))
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

    def _disp_key(self, cli_args, k):
        if cli_args['--hide-keys']:
            # number of digits to show
            num = 10
            return k[:num] + '?' * len(k[num:])  
        else:
            return k

    def _print_node(self, rid, info, aliases, cli_args, spacer, islast):
        typ = info['basic']['type']
        id = 'cik: ' + self._disp_key(cli_args, info['key']) if typ=='client' else 'rid: ' + self._disp_key(cli_args, rid)
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
        if typ == 'client':
            add_opt('--verbose', 'rid', self._disp_key(cli_args, rid))
        if info.has_key('storage') and info['storage'].has_key('count'):
            add_opt(True, 'count', info['storage']['count'])
        
        print(u'{}{} {}'.format(
            spacer,
            id,
            u'' if len(opt) == 0 else u'({})'.format(u', '.join(
                [u'{}: {}'.format(k, v) for k, v in opt.iteritems()]))))

    def tree(self, cik, aliases=None, cli_args={}, spacer=u''): 
        '''Print a tree of entities in OneP'''
        # print root node
        isroot = len(spacer) == 0
        if isroot:
            print(self._disp_key(cli_args, cik))

        types = ['dataport', 'datarule', 'dispatch', 'client']
        listing = self.listing_with_info(cik, types=types)
        # previously: [['<rid0>', '<rid1>'], ['<rid2>'], [], ['<rid3>']] 
        # now: [{'<rid0>':<info0>, '<rid1>':<info1>}, {'<rid2>':<info2>}, [], {'<rid3>': <info3>}] 

        # print everything
        for t_idx, t in enumerate(types):
            typelisting = listing[t_idx]
            islast_nonempty_type = (t_idx == len(types) - 1) or (all(len(x) == 0 for x in listing[t_idx + 1:]))
            for rid_idx, rid in enumerate(typelisting):
                info = typelisting[rid]
                islastoftype = rid_idx == len(typelisting) - 1
                islast = islast_nonempty_type and islastoftype
                if islast:
                    child_spacer = spacer + u'    '
                    own_spacer   = spacer + u'  └─' 
                else:
                    child_spacer = spacer + u'  │ '
                    own_spacer   = spacer + u'  ├─'

                if t == 'client':
                    next_cik = info['key']
                    self._print_node(rid, info, aliases, cli_args, own_spacer, islast)
                    self.tree(next_cik, info['aliases'], cli_args, child_spacer)
                else:
                    self._print_node(rid, info, aliases, cli_args, own_spacer, islast)
                   
    def drop_all_children(self, cik):
        isok, listing = self.exo.listing(cik, 
            types=['client', 'dataport', 'datarule', 'dispatch'])
        self._raise_for_response(isok, listing)

        for l in listing:
            self.drop(cik, l)

    def _lookup_rid_by_name(self, cik, name, types=['datarule']):
        '''Look up RID by name. We use name rather than alias to identify 
        scripts created in Portals, which only shows names, not aliases. 
        Note that if multiple scripts have the same name, the first one 
        in the listing is returned.'''
        found_rid = None
        listing = self.listing_with_info(cik, types)
        for type_listing in listing:
            for rid in type_listing:
                if type_listing[rid]['description']['name'] == name:
                    # return first match
                    return rid
        return None

    def _upload_script(self, cik, name, text, rid=None, meta=''):
        '''Upload a lua script, either creating one or updating the existing one'''
        desc = {
            'format': 'string',
            'name': name,
            'preprocess': [],
            'rule': {
                'script': text 
            },
            'visibility': 'parent',
            'retention': {
                'count': 'infinity',
                'duration': 'infinity' 
            }
        }

        if rid is None:
            success, rid = self.exo.create(cik, 'datarule', desc)
            if success:
                print("New script RID: {}".format(rid))
            else:
                #print('cik: {} desc: {}'.format(cik, json.dumps(desc)))
                raise ExoException("Error creating datarule: {}".format(rid))
            success, rid = self.exo.map(cik, rid, name)
            if success:
                print("Aliased script to: {}".format(name))
            else:
                raise ExoException("Error aliasing script")
        else:
            success = self.exo.update(cik, rid, desc)
            if success:
                print ("Updated script RID: {}".format(rid))
            else:
                raise ExoException("Error updating datarule.")

            
    def upload(self, cik, filename, name=None):
        try:
            f = open(filename)
        except IOError as ex:
            raise ExoException('Error opening file.')
        else:
            with f:
                text = f.read().strip()
                if name is None:
                    # if no name is specified, use the file name as a name 
                    name = os.path.basename(filename)
                rid = self._lookup_rid_by_name(cik, name) 
                self._upload_script(cik, name, text, rid) 


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

    def record_backdate(self, cik, rid, interval_seconds, values):
        '''Record a list of values and record them as if they happened in the past
        interval_seconds apart. For example, if values ['a', 'b', 'c'] are passed in 
        with interval 10, they're recorded as [[0, 'c'], [-10, 'b'], [-20, 'a']]'''
        timestamp = -interval_seconds 
        tvalues = []
        values.reverse()
        for v in values:
            tvalues.append([timestamp, v])
            timestamp -= interval_seconds
        return self.record(cik, rid, tvalues)

       
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
        rid = rids[0]
        limit = args['--limit']
        limit = 1 if limit is None else int(limit)
        dr = csv.DictWriter(sys.stdout, ['timestamp', 'value'])
        def printline(timestamp, val):
            dt = datetime.fromtimestamp(timestamp)
            dr.writerow({'timestamp': str(dt), 'value': val})
        sleep_seconds = 2 
        if args['--follow']:
            try:
                results = []
                while len(results) == 0:
                    results = er.read(cik, 
                                      rid, 
                                      limit=1,
                                      sort='desc')
                    if len(results) > 0:
                        last_t, last_v = results[0]
                        printline(last_t, last_v)
                    else:
                        time.sleep(sleep_seconds)


                while True:
                    results = er.read(cik, 
                                      rid,
                                      limit=10000,
                                      starttime=last_t + 1)

                    for t, v in results:
                        printline(t, v)

                    if len(results) > 0:
                        last_t, last_v = results[-1]

                    time.sleep(sleep_seconds)
            except KeyboardInterrupt:
                pass
        else:
            for t, v in er.read(cik,
                                rid,
                                sort='desc',
                                limit=limit):
                printline(t, v)
    elif args['write']:
        tvalues = args['--value']
        er.write(cik, rids[0], tvalues)
    elif args['record']:
        entries = []
        # split timestamp, value
        if args['-']:
            tvalues = sys.stdin.readlines()
        else:
            tvalues = args['--value']
            
        reentry = re.compile('(-?\d+),(.*)')
        has_errors = False
        for tv in tvalues:
            match = reentry.match(tv)    
            if match is None:
                sys.stderr.write('Line not in <timestamp>,<value> format: {}'.format(tv))
                has_errors = True
            else:
                g = match.groups()
                entries.append([int(g[0]), g[1]])
        if has_errors or len(entries) == 0:
            raise ExoException("Problems with input.")
        else:
            er.record(cik, rids[0], entries)
    elif args['create']:
        s = sys.stdin.read()
        try:
            desc = json.loads(s)
        except Exception as ex:
            raise ExoException(ex)
        pr(er.create(cik, type=args['--type'][0], desc=desc))
    elif args['create-dataport']:
        pr(er.create_dataport(cik, args['--format'], name=args['--name']))
    elif args['create-client']:
        pr(er.create_client(cik, name=args['--name']))
    elif args['map']:
        er.map(cik, rids[0], args['<alias>'])
    elif args['unmap']:
        er.unmap(cik, args['<alias>'])
    elif args['lookup']:
        pr(er.lookup(cik, args['<alias>']))
    elif args['drop']:
        er.drop(cik, rids)
    elif args['listing']:
        types = args['--type']
        listing = er.listing(cik, types)
        if args['--plain'] == True:
            if len(types) != 1:
                raise ExoException("--plain not valid with more than one type")
            for cik in listing[0]:
                print(cik)
        else:
            pr(listing)
    elif args['info']:
        info = er.info(cik, rids[0], cikonly=args['--cikonly'])
        if args['--pretty']:
            pr(info)
        else:
            # output json
            pr(json.dumps(info))
    elif args['flush']:
        er.flush(cik, rids)
    # special commands
    elif args['tree']:
        er.tree(cik, cli_args=args)
    elif args['lookup-rid']:
        rid = er.lookup_rid(cik, args['<cik-to-find>'])
        if rid is not None:
            pr(rid)
    elif args['drop-all-children']:
        er.drop_all_children(cik)
    elif args['upload']:
        er.upload(cik, args['<script-file>'], args['--name'])
    elif args['record-backdate']:
        # split timestamp, value
        if args['-']:
            values = [v.strip() for v in sys.stdin.readlines()]
        else:
            values = args['--value']
        er.record_backdate(cik, rids[0], int(args['--interval']), values)


if __name__ == '__main__':
    args = docopt(__doc__, version="Exosite RPC API Command Line {}".format(__version__))
    # substitute environment variables
    if args['--host'] is None:
        args['--host'] = os.environ.get('EXO_HOST', DEFAULT_HOST)

    # support passing aliases
    rids = []
    for rid in args['<rid>']:
        if re.match("[0-9a-zA-Z]{40}", rid) is None:
            rids.append({"alias": rid})
        else:
            rids.append(rid)

    try:
        handle_args(args)
    except ExoException as ex:
        # command line tool threw an exception on purpose
        sys.stderr.write("Command line error: {}\r\n".format(ex))
        sys.exit(1)
    except RPCException as ex:
        # pyonep library call signaled an error in return values 
        sys.stderr.write("One Platform error: {}\r\n".format(ex))
        sys.exit(1)
    except onep_exceptions.OnePlatformException as ex:
        # pyonep library call threw an exception on purpose
        sys.stderr.write("One Platform exception: {}\r\n".format(ex))
        sys.exit(1)
