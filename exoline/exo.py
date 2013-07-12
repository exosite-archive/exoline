#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Exosite RPC API Command Line Interface
   Provides command line access to the Remote Procedure Call API:
   http://developers.exosite.com/display/OP/Remote+Procedure+Call+API

Usage:
  exo [options] <command> [<args> ...]

Commands:
  read
  write
  record
  create
  create-dataport
  create-client
  update
  map
  unmap
  lookup
  drop
  listing
  info
  flush
  tree
  lookup-rid
  drop-all-children
  script

Options:
  --host=<host>        OneP URL. Default is $EXO_HOST or m2.exosite.com.
  --httptimeout=<sec>  HTTP timeout setting.
  --https              Enable HTTPS
  --debug              Show info like stack traces
  -h --help            Show this screen.
  -v --version         Show version.

See 'exo <command> -h' for more information on a specific command.
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
cmd_doc = {
    'read': '''Read data from a resource.\n\nUsage:
    exo [options] read <cik> [<rid>]

Options:
    --follow          continue reading
    --limit=<limit>   limit to [default: 1]
    --selection=all|autowindow|givenwindow  how to filter results [default: all]
    --format=raw|csv output format [default: csv]''',
    'write': '''Write data at the current time.\n\nUsage:
    exo [options] write <cik> [<rid>] --value=<value>''',
    'record': '''Write data at a specified time.\n\nUsage:
    exo [options] record <cik> [<rid>] ((--value=<timestamp,value> ...) | -)
    exo [options] record <cik> [<rid>] --interval=<seconds> ((--value=<value> ...) | -)

    Pass - to read data from stdin.
    Pass --interval to generate timestamps at a regular interval from now.
    If --interval is positive, data will be placed in the future. If it's
    negative, data will be placed in the past.''',
    'create': '''Create a resource from a json description passed on stdin.\n\nUsage:
    exo [options] create <cik> (--type=client|clone|dataport|datarule|dispatch) -''',
    'listing': '''List a client's children based on their type.\n\nUsage:
    exo [options] listing <cik> (--type=client|dataport|datarule|dispatch) ... [--plain] [--pretty]''',
    'info': '''Get info for a resource in json format.\n\nUsage:
    exo [options] info <cik> [<rid>] [--cikonly] [--pretty]''',
    'create-dataport': '''Create a dataport.\n\nUsage:
    exo [options] create-dataport <cik> (--format=binary|boolean|float|integer|string) [--name=<name>]''',
    'create-client': '''Create a client.\n\nUsage:
    exo [options] create-client <cik> [--name=<name>]''',
    'update': '''Update a resource from a json description passed on stdin.\n\nUsage:
    exo [options] update <cik> [<rid>] -

Restrictions:

Client Description
    Resource limits must not be lowered below current use level. Resources must be
    dropped prior to lowering the limits. For daily limits, those may be lowered at
    any point and take immediate affect.

Dataport Description
    Format must not be changed.

Datarule Descriptions
    Format must not be changed.

Dispatch Description
    If the recipient or method is changed, and the recipient/method combination has
    never been used before, then further dispatches will be halted until a
    Validation Request is sent and validated.''',
    'map': '''Add an alias to a resource.\n\nUsage:
    exo [options] map <cik> <rid> <alias>''',
    'unmap': '''Remove an alias from a resource.\n\nUsage:
    exo [options] unmap <cik> <alias>''',
    'lookup': '''Look up a resource's RID based on its alias or cik.\n\nUsage:
    exo [options] lookup <cik> <alias>
    exo [options] lookup <cik> --cik=<cik-to-find>''',
    'drop': '''Drop (permanently delete) a resource.\n\nUsage:
    exo [options] drop <cik> <rid> ...''',
    'flush': '''Remove all time series data from a resource.\n\nUsage:
    exo [options] flush <cik> <rid>''',
    'tree': '''Display a resource's descendants.\n\nUsage:
    exo tree [--verbose] [--hide-keys] <cik>''',
    'drop-all-children': '''Drop (delete permanently) all children of a resource.\n\nUsage:
    exo [options] drop-all-children <cik>''',
    'script': '''Upload a Lua script\n\nUsage:
    exo [options] script <script-file> <cik> [--name=<name>]'''
}

for k in cmd_doc:
    cmd_doc[k] += '''

Options:
    -h --help            Show this screen.'''

class ExoException(Exception):
    pass

class RPCException(Exception):
    pass

class ExoRPC():
    '''Wrapper for onepv1lib RPC API. Raises exceptions on error and provides some reasonable defaults.'''
    def __init__(self,
            host='http://' + DEFAULT_HOST,
            httptimeout=60,
            https=False,
            verbose=True):
        port = {False: '80', True: '443'}[https]
        self.exo = onep.OnepV1(host=host, httptimeout=httptimeout, https=https, port=port)

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

    def write(self, cik, rid, value):
        isok, response = self.exo.write(cik, rid, value, {})
        self._raise_for_response(isok, response)

    def record(self, cik, rid, entries):
        isok, response = self.exo.record(cik, rid, entries, {})
        self._raise_for_response_record(isok, response)

    def create(self, cik, type, desc):
        isok, response = self.exo.create(cik, type, desc)
        self._raise_for_response(isok, response)
        return response

    def update(self, cik, rid, desc):
        isok, response = self.exo.create(cik, rid, desc)
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
        print(self.exo.lookup(cik, 'alias', alias))
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
            if not 'key' in response:
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
        if typ == 'client':
            id = 'cik: ' + self._disp_key(cli_args, info['key'])
        else:
            id = 'rid: ' + self._disp_key(cli_args, rid)
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
            if o is True or (o in cli_args and cli_args[o] is True):
                opt[label] = value
        add_opt(True, 'type', typ)
        if 'format' in info['description']:
            add_opt(True, 'format', info['description']['format'])
        add_opt(True, 'name', name)
        add_opt(True, 'aliases', str(aliases))
        add_opt('--verbose', 'unit', units)
        if typ == 'client':
            add_opt('--verbose', 'rid', self._disp_key(cli_args, rid))
        if 'storage' in info and 'count' in info['storage']:
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
            # todo: combine these (maybe also the listing_with_info function
            # below?)
            rid = self.lookup(cik, "")
            info = self.info(cik, {"alias": ""})
            # info doesn't contain key
            info['key'] = cik
            root_aliases = '(see parent)'
            # todo: can I get aliases for cik? For now, pass []
            self._print_node(rid,
                             info,
                             root_aliases,
                             cli_args,
                             spacer,
                             islast=True)

        types = ['dataport', 'datarule', 'dispatch', 'client']
        try:
            listing = self.listing_with_info(cik, types=types)
            # listing(): [['<rid0>', '<rid1>'], ['<rid2>'], [], ['<rid3>']]
            # listing_with_info(): [{'<rid0>':<info0>, '<rid1>':<info1>},
            #                       {'<rid2>':<info2>}, [], {'<rid3>': <info3>}]
        except onep_exceptions.OnePlatformException:
            print(spacer + u"  └─listing for {} failed. Is info['basic']['status'] == 'expired'?".format(cik))
        else:
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
        except IOError:
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

def handle_args(cmd, args):
    er = ExoRPC(host=args['--host'], https=args['--https'])
    cik = args['<cik>']

    def rid_or_alias(rid):
        '''Translate what was passed for <rid> to an alias object if
           it doesn't look like a RID.'''
        if re.match("[0-9a-zA-Z]{40}", rid) is None:
            return {"alias": rid}
        else:
            return rid

    rids = []
    if '<rid>' in args:
        if type(args['<rid>']) is list:
            for rid in args['<rid>']:
                rids.append(rid_or_alias(rid))
        else:
            if args['<rid>'] is None:
                rids.append({"alias": ""})
            else:
                rids.append(rid_or_alias(args['<rid>']))

    if args.get('--pretty', False):
        pr = pprint
    else:
        pr = plain_print

    if cmd == 'read':
        rid = rids[0]
        limit = args['--limit']
        limit = 1 if limit is None else int(limit)
        dr = csv.DictWriter(sys.stdout, ['timestamp', 'value'])
        fmt = args['--format']

        def printline(timestamp, val):
            if fmt == 'raw':
                print(val)
            else:
                dt = datetime.fromtimestamp(timestamp)
                dr.writerow({'timestamp': str(dt), 'value': val})

        sleep_seconds = 2
        if args['--follow']:
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
        else:
            for t, v in er.read(cik,
                                rid,
                                sort='desc',
                                limit=limit):
                printline(t, v)
    elif cmd == 'write':
        er.write(cik, rids[0], args['--value'])
    elif cmd == 'record':
        interval = args['--interval']
        if interval is not None:
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
                    sys.stderr.write(
                        'Line not in <timestamp>,<value> format: {}'.format(tv))
                    has_errors = True
                else:
                    g = match.groups()
                    entries.append([int(g[0]), g[1]])
            if has_errors or len(entries) == 0:
                raise ExoException("Problems with input.")
            else:
                er.record(cik, rids[0], entries)
        else:
            # split timestamp, value
            if args['-']:
                values = [v.strip() for v in sys.stdin.readlines()]
            else:
                values = args['--value']
            er.record_backdate(cik, rids[0], int(interval), values)


    elif cmd == 'create':
        s = sys.stdin.read()
        try:
            desc = json.loads(s)
        except Exception as ex:
            raise ExoException(ex)
        pr(er.create(cik, type=args['--type'], desc=desc))
    elif cmd == 'update':
        s = sys.stdin.read()
        try:
            desc = json.loads(s)
        except Exception as ex:
            raise ExoException(ex)
        pr(er.update(cik, rids[0], desc=desc))
    elif cmd == 'create-dataport':
        pr(er.create_dataport(cik, args['--format'], name=args['--name']))
    elif cmd == 'create-client':
        pr(er.create_client(cik, name=args['--name']))
    elif cmd == 'map':
        er.map(cik, rids[0], args['<alias>'])
    elif cmd == 'unmap':
        er.unmap(cik, args['<alias>'])
    elif cmd == 'lookup':
        # look up by cik or alias
        if args['--cik'] is not None:
            rid = er.lookup_rid(cik, args['--cik'])
            if rid is not None:
                pr(rid)
        else:
            pr(er.lookup(cik, args['<alias>']))
    elif cmd == 'drop':
        er.drop(cik, rids)
    elif cmd == 'listing':
        types = args['--type']
        listing = er.listing(cik, types)
        if args['--plain'] == True:
            for l in listing:
                for cik in listing[0]:
                    print(cik)
        else:
            pr(listing)
    elif cmd == 'info':
        info = er.info(cik, rids[0], cikonly=args['--cikonly'])
        if args['--pretty']:
            pr(info)
        else:
            # output json
            pr(json.dumps(info))
    elif cmd == 'flush':
        er.flush(cik, rids)
    # special commands
    elif cmd == 'tree':
        er.tree(cik, cli_args=args)
    elif cmd == 'drop-all-children':
        er.drop_all_children(cik)
    elif cmd == 'script':
        er.upload(cik, args['<script-file>'], args['--name'])
    else:
        raise ExoException("Command not handled")

if __name__ == '__main__':

    args = docopt(__doc__,
                  version="Exosite RPC API Command Line {}".format(__version__), options_first=True)

    # get command args
    cmd = args['<command>']
    argv = [cmd] + args['<args>']
    if cmd in cmd_doc:
        args_cmd = docopt(cmd_doc[cmd], argv=argv)
    else:
        print('Unknown command {}. Try "exo --help"'.format(cmd))
        sys.exit(1)

    # merge command-specific arguments into general arguments
    args.update(args_cmd)

    # substitute environment variables
    if args['--host'] is None:
        args['--host'] = os.environ.get('EXO_HOST', DEFAULT_HOST)

    try:
        handle_args(cmd, args)
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
    except KeyboardInterrupt:
        if args['--debug']:
            raise
