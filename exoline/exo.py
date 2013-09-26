#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Exosite RPC API Command Line Interface
   Provides command line access to the Remote Procedure Call API:
   https://github.com/exosite/api/tree/master/rpc

Usage:
  exo [--help] [options] <command> [<args> ...]

Commands:
  {{ command_list }}
Options:
  --host=<host>        OneP URL. Default is $EXO_HOST or m2.exosite.com
  --port=<port>        OneP port. Default is $EXO_HOST or 80
  --httptimeout=<sec>  HTTP timeout [default: 60]
  --https              Enable HTTPS
  --debug              Show info like stack traces
  --debughttp          Turn on debug level loggin in pyonep
  --discreet           Obfuscate RIDs in stdout and stderr
  -h --help            Show this screen
  -v --version         Show version

See 'exo <command> --help' for more information on a specific command.
"""

# Copyright (c) 2013, Exosite, LLC
# All rights reserved
import sys
import os
import json
import csv
import re
from datetime import datetime
from datetime import timedelta
import time
from pprint import pprint
from operator import itemgetter
import logging
from collections import defaultdict
import StringIO
# python 2.6 support
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
import itertools
import math

from docopt import docopt
from dateutil import parser
import requests
import yaml

from pyonep import onep
import pyonep
try:
    from ..exoline import __version__
    from ..exoline.exocommon import ExoException
except:
    from exoline import __version__
    from exocommon import ExoException


DEFAULT_HOST = 'm2.exosite.com'
DEFAULT_PORT = '80'
DEFAULT_PORT_HTTPS = '443'

cmd_doc = {
    'read':
        '''Read data from a resource.\n\nUsage:
    exo [options] read <cik> [<rid> ...]

Options:
    --follow                 continue reading (ignores --end)
    --limit=<limit>          number of data points to read [default: 1]
    --start=<time>
    --end=<time>             start and end times (see details below)
    --sort=<order>           asc or desc [default: desc]
    --selection=all|autowindow|givenwindow  downsample method [default: all]
    --format=csv|raw         output format [default: csv]
    --timeformat=unix|human|iso8601
                             unix timestamp or human-readable? [default: human]
    --header=name|rid        include a header row
    --chunkhours=<hours>     break read into multiple requests of length
                             <hours>, printing data as it is received and
                             ignoring --limit. Note that this requires start
                             and end time be set.
    {{ helpoption }}

    If <rid> is omitted, reads all datasources and datarules under <cik>.

    {{ startend }}''',
    'write':
        '''Write data at the current time.\n\nUsage:
    exo [options] write <cik> [<rid>] --value=<value>''',
    'record':
        '''Write data at a specified time.\n\nUsage:
    exo [options] record <cik> [<rid>] ((--value=<timestamp,value> ...) | -)
    exo [options] record <cik> [<rid>] --interval=<seconds> ((--value=<value> ...) | -)

    - reads data from stdin.
    --interval generates timestamps at a regular interval into the past.''',
    'create':
        '''Create a resource from a json description passed on stdin, or using
    defaults.\n\nUsage:
    exo [options] create <cik> (--type=client|clone|dataport|datarule|dispatch) -
    exo [options] create <cik> --type=client
    exo [options] create <cik> --type=dataport (--format=binary|boolean|float|integer|string)

Options:
    --name=<name     set a resource name (overwriting the one in stdin if present)
    --alias=<alias>  set an alias
    --ridonly        output the RID by itself on a line
    --cikonly        output the CIK by itself on a line (--type=client only)
    {{ helpoption }}

Details:
    Pass - and a json description object on stdin, or leave it off to use defaults.
    Description is documented here:
    http://developers.exosite.com/display/OP/Remote+Procedure+Call+API#RemoteProcedureCallAPI-create

    If - is not present, creates a resource with common defaults.''',
    'listing':
        '''List the RIDs of a client's children.\n\nUsage:
    exo [options] listing <cik> [(--type=client|dataport|datarule|dispatch) ...]

    If --type is omitted, it defaults to:
    --type=client --type=dataport --type=datarule --type=dispatch

Options:
    --plain   show only the child RIDs
    --pretty  pretty print output''',
    'info':
        '''Get metadata for a resource in json format.\n\nUsage:
    exo [options] info <cik> [<rid>]

Options:
    --cikonly      print CIK by itself
    --pretty       pretty print output
    --recursive    embed info for any children recursively
    --include=<key list>
    --exclude=<key list>
                   comma separated list of info keys to include and exclude.
                   Available keys are aliases, basic, counts, description,
                   key, shares, storage, subscribers, tags, usage. If omitted,
                   all available keys are returned.''',
    'update':
        '''Update a resource from a json description passed on stdin.\n\nUsage:
    exo [options] update <cik> (<rid> - | -)


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
    'map':
        '''Add an alias to a resource.\n\nUsage:
    exo [options] map <cik> <rid> <alias>''',
    'unmap':
        '''Remove an alias from a resource.\n\nUsage:
    exo [options] unmap <cik> <alias>''',
    'lookup':
        '''Look up a resource's RID based on its alias or cik.\n\nUsage:
    exo [options] lookup <cik> [<alias>]
    exo [options] lookup <cik> --cik=<cik-to-find>

    If <alias> is omitted, the rid for <cik> is returned. This is equivalent to:

    exo lookup <cik> ""''',
    'drop':
        '''Drop (permanently delete) a resource.\n\nUsage:
    exo [options] drop <cik> [<rid> ...]

Options:
    --all-children  drop all children of the resource.
    {{ helpoption }}''',
    'flush':
        '''Remove all time series data from a resource.\n\nUsage:
    exo [options] flush <cik> [<rid>]''',
    'usage':
        '''Display usage of One Platform resources over a time period.\n\nUsage:
    exo [options] usage <cik> [<rid>] --start=<time> [--end=<time>]

    {{ startend }}''',
    'tree': '''Display a resource's descendants.\n\nUsage:
    exo [options] tree [--verbose] <cik>

    --counts       show item counts (from info.storage.counts)
    --level=<num>  depth to traverse, omit or -1 for no limit [default: -1]''',
    'ut': '''Display a tree as fast as possible\n\nUsage:
    exo [options] ut <cik>''',
    'script': '''Upload a client's a Lua script\n\nUsage:
    exo [options] script <script-file> <cik> ...

Options:
    --name=<name>  script name, if different from script filename. The name
                   is used to identify the script, too.
    --recursive    operate on client and any children
    --create       create the script if it doesn't already exist''',
    'spark': '''Show distribution of intervals between points.\n\nUsage:
    exo [options] spark <cik> [<rid>] --days=<days>

Options:
    --stddev=<num>  exclude intervals more than num standard deviations from mean
    {{ helpoption }}''',
    'copy': '''Make a copy of a client.\n\nUsage:
    exo [options] copy <cik> <destination-cik>

    Copies <cik> and all its non-client children to <destination-cik>.
    Returns CIK of the copy. NOTE: copy excludes all data in dataports.

Options:
    --cikonly  show unlabeled CIK by itself
    {{ helpoption }}''',
    'diff': '''Show differences between two clients.\n\nUsage:
    exo [options] diff <cik> <cik2>

    Displays differences between <cik> and <cik2>, including all non-client
    children. If clients are identical, nothing is output. For best results,
    all children should have unique names.

Options:
    --full         compare all info, even usage, data counts, etc.
    --no-children  don't compare children
    {{ helpoption }}''',
    'ip': '''Get IP address of the server.\n\nUsage:
    exo [options] ip''',
    'data': '''Read or write with the HTTP Data API.\n\nUsage:
    exo [options] data <cik> [--write=<alias,value> ...] [--read=<alias> ...]

    If only --write arguments are specified, the call is a write.
    If only --read arguments are specified, the call is a read.
    If both --write and --read arguments are specified, the hybrid
        write/read API is used. Writes are executed before reads.'''
    }

# shared sections of documentation
doc_replace = {
    '{{ startend }}': '''<time> can be a unix timestamp or formatted like any of these:

    2011-10-23T08:00:00-07:00
    10/1/2012
    "2012-10-23 14:01"

    If time part is omitted, it assumes 00:00:00.
    To report through the present time, omit --end or pass --end=now''',
    '{{ helpoption }}': '''-h --help  Show this screen.''',
}

# load plugins
import importlib
import plugins as plugins_package
#plugin_path = os.path.dirname(os.path.realpath(plugins_package.__file__))
plugins = []
for module_name in plugins_package.__all__:
    #plugin = imp.load_module(module_name, *imp.find_module(module_name, [plugin_path]))

    try:
        plugin = importlib.import_module('plugins.' + module_name)
    except:
        plugin = importlib.import_module('exoline.plugins.' + module_name, package='test')

    # instantiate plugin
    p = plugin.Plugin()
    plugins.append(p)

    # get documentation
    cmd_doc[p.command()] = plugin.__doc__


# perform substitutions on command documentation
for k in cmd_doc:
    # helpoption is appended to any commands that don't already have it
    if '{{ helpoption }}' not in cmd_doc[k]:
        cmd_doc[k] += '\n\nOptions:\n{{ helpoption }}'
    for r in doc_replace:
        cmd_doc[k] = cmd_doc[k].replace(r, doc_replace[r])




class ExolineOnepV1(onep.OnepV1):
    '''Subclass that re-adds deprecated commands used by Portals'''
    def comment(self, cik, rid, visibility, comment, defer=False):
        return self._call('comment', cik, [rid, visibility, comment], defer)


class ExoRPC():
    '''Wrapper for pyonep RPC API.
    Raises exceptions on error and provides some reasonable defaults.'''
    regex_rid = re.compile("[0-9a-zA-Z]{40}")

    class RPCException(Exception):
        pass

    def __init__(self,
                 host=DEFAULT_HOST,
                 port=None,
                 httptimeout=60,
                 https=False,
                 verbose=True):

        if port is None:
            port = DEFAULT_PORT_HTTPS if https else DEFAULT_PORT
        self.exo = ExolineOnepV1(host=host,
                               port=port,
                               httptimeout=httptimeout,
                               https=https,
                               agent="Exoline {0}".format(__version__))

    def _raise_for_response(self, isok, response, call=None):
        if not isok:
            if call is None:
                msg = str(response)
            else:
                msg = '{0} ({1})'.format(str(response), str(call))
            raise ExoRPC.RPCException(msg)

    def _raise_for_response_record(self, isok, response):
        '''Undocumented RPC behavior-- if record timestamps are invalid, isok
           is True but response is an array of timestamps and error
           messages.'''
        self._raise_for_response(isok, response)
        if type(response) is list:
            # TODO: does this always indicate an error condition?
            raise ExoRPC.RPCException(', '.join(['{0}: {1}'.format(msg, t) for msg, t in response]))

    def _raise_for_deferred(self, responses):
        r = []
        for call, isok, response in responses:
            self._raise_for_response(isok, response, call=call)
            r.append(response)
        return r

    def _exomult(self, cik, commands):
        '''Takes a list of onep commands with cik omitted, e.g.:
            [['info', {alias: ""}], ['listing']]'''
        if len(commands) == 0:
            return []
        assert(not self.exo.has_deferred(cik))
        for c in commands:
            if type(c) is not list:
                raise Exception("_exomult: found invalid command")
            method = getattr(self.exo, c[0])
            #print c
            method(cik, *c[1:], defer=True)
        assert(self.exo.has_deferred(cik))
        responses = self._raise_for_deferred(self.exo.send_deferred(cik))
        return responses

    def _readoptions(self, limit, sort, starttime, endtime, selection):
        options ={'limit': limit,
                  'sort': sort,
                  'selection': selection}
        if starttime is not None:
            options['starttime'] = int(starttime)
        if endtime is not None:
            options['endtime'] = int(endtime)
        return options

    def lookup_shortcut(self, cik):
        '''Look up what was passed for cik in config file
            if it doesn't look like a CIK.'''
        if self.regex_rid.match(cik) is None:
            # if cik doesn't look like a cik, maybe it's a shortcut
            configfile = os.path.join(os.environ['HOME'], '.exoline')
            try:
                with open(configfile) as f:
                    config = yaml.safe_load(f)
                    if 'keys' in config:
                        if cik in config['keys']:
                            return config['keys'][cik].strip()
                        else:
                            raise ExoException('No CIK shortcut {0}\n{1}'.format(
                                cik,
                                '\n'.join(config['keys'])))
                    else:
                        raise ExoException('Tried a CIK shortcut {0}, but found no keys in {1}'.format(
                            cik,
                            configfile))
            except IOError as ex:
                raise ExoException(
                    'Tried a CIK shortcut {0}, but couldn\'t open {1}'.format(
                    cik,
                    configfile))
        else:
            return cik

    def read(self,
             cik,
             rid,
             limit,
             sort='asc',
             starttime=None,
             endtime=None,
             selection='all'):
        options = self._readoptions(limit, sort, starttime, endtime, selection)
        isok, response = self.exo.read(
            cik,
            rid,
            options)
        self._raise_for_response(isok, response)
        return response

    def _combinereads(self, reads, sort):
        '''
        >>> exo = ExoRPC()
        >>> exo._combinereads([[[2, 'a'], [1, 'b']]])
        [[2, ['a']], [1, ['b']]]
        >>> exo._combinereads([[[3, 'a'], [2, 'b']], [[3, 77], [1, 78]]])
        [[3, ['a', 77]], [2, ['b', None]], [1, [None, 78]]]
        >>> exo._combinereads([[[5, 'a'], [4, 'b']], [[2, 'd'], [1, 'e']]])
        [[5, ['a', None]], [4, ['b', None]], [2, [None, 'd']], [1, [None, 'e']]]
        >>> exo._combinereads([])
        []
        '''
        if len(reads) == 0:
            return []
        else:
            combined = []

            # indexes into each list indicating the next
            # unprocessed value
            curi = [len(l) - 1 for l in reads]
            #print(reads)

            # loop until we've processed every element
            while curi != [-1] * len(curi):
                # minimum timestamp from unprocessed entries
                timestamp = min([reads[i][ci] for i, ci in enumerate(curi) if ci is not -1],
                        key=itemgetter(0))[0]

                # list of points we haven't processed in each read result
                # (or None, if all have been processed)
                unprocessed = [r[i] if i > -1 else None for i, r in zip(curi, reads)]

                # list of values corresponding to timestamp t
                values = [None if p is None or p[0] != timestamp else p[1]
                        for p in unprocessed]

                #print('curi {}, values {}, unprocessed: {}'.format(curi, values, unprocessed))

                # add to combined results
                combined.append([timestamp, values])

                # update curi based on which values were processed
                for i, v in enumerate(values):
                    if v is not None:
                        curi[i] -= 1

            if sort == 'desc':
                reverse = True
            else:
                reverse = False

            combined.sort(key=itemgetter(0), reverse=reverse)
            return combined

    def readmult(self,
                 cik,
                 rids,
                 limit,
                 sort='asc',
                 starttime=None,
                 endtime=None,
                 selection='all',
                 chunkhours=None):
        '''Generates multiple rids and returns combined timestamped data like this:
               [12314, [1, 77, 'a']
               [12315, [2, 78, None]]
           Where 1, 77, 'a' is the order rids were passed, and None represents
           no data in that dataport for that timestamp.'''
        options = self._readoptions(limit, sort, starttime, endtime, selection)

        def _read(cik, rids, options):
            responses = self._exomult(cik, [['read', rid, options] for rid in rids])
            return self._combinereads(responses, options['sort'])

        def _read_chunk(cik, rids, options, start, end):
            chunkoptions = options.copy()
            chunkoptions['starttime'] = start
            chunkoptions['endtime'] = end
            # read all points
            chunkoptions['limit'] = end - start
            return _read(cik, rids, chunkoptions)

        if chunkhours is None:
            for r in _read(cik, rids, options):
                yield r
        else:

            # maximum # seconds we want to read in one request
            # TODO: is there a clever way to calculate optimal read
            # sizes automatially? What users want is 1.) no
            # timeout/onep error and 2.) progress indication of some kind.
            # I'd rather the user not have to figure out chunkhours
            # themselves.
            max_sec = 60 * 60 * int(chunkhours)

            # TODO: figure out whether it's probably a large read by reading
            # info, usage, or by some calculation.
            is_large_read = True

            # TODO: figure out earliest timestamp with data and adjust
            # starttime if necessary.

            if is_large_read:

                if 'sort' in options and options['sort'] == 'desc':
                    # descending
                    for end in range(options['endtime'],
                                     options['starttime'],
                                     -max_sec):
                        start = max(end - max_sec, options['starttime'])
                        for r in _read_chunk(cik, rids, options, start, end):
                            yield r
                else:
                    # ascending
                    for start in range(options['starttime'],
                                       options['endtime'],
                                       max_sec):
                        end = min(start + max_sec, options['endtime'])
                        for r in _read_chunk(cik, rids, options, start, end):
                            yield r

            else:
                # make a single request
                for r in _read(cik, rids, options):
                    yield r

    def write(self, cik, rid, value):
        isok, response = self.exo.write(cik, rid, value)
        self._raise_for_response(isok, response)

    def record(self, cik, rid, entries):
        isok, response = self.exo.record(cik, rid, entries, {})
        self._raise_for_response_record(isok, response)

    def create(self, cik, type, desc, name=None):
        if name is not None:
            desc['name'] = name
        isok, response = self.exo.create(cik, type, desc)
        self._raise_for_response(isok, response)
        return response

    def update(self, cik, rid, desc):
        isok, response = self.exo.update(cik, rid, desc)
        self._raise_for_response(isok, response)
        return response

    def create_dataport(self, cik, format, name=None):
        '''Create a dataport child of cik with common defaults.
           (retention count duration set to "infinity"). Returns
           RID string of the created dataport.'''
        desc = {"format": format,
                "retention": {
                    "count": "infinity",
                    "duration": "infinity"}
                }
        if name is not None:
            desc['name'] = name
        return self.create(cik, 'dataport', desc)

    def create_client(self, cik, name=None, desc=None):
        '''Create a client child of cik with common defaults.
        ('inherit' set for all limits). Returns RID string
        of the created client.'''
        if desc is None:
            # default description
            desc = {'limits': {'client': 'inherit',
                               'dataport': 'inherit',
                               'datarule': 'inherit',
                               'disk': 'inherit',
                               'dispatch': 'inherit',
                               'email': 'inherit',
                               'email_bucket': 'inherit',
                               'http': 'inherit',
                               'http_bucket': 'inherit',
                               'share': 'inherit',
                               'sms': 'inherit',
                               'sms_bucket': 'inherit',
                               'xmpp': 'inherit',
                               'xmpp_bucket': 'inherit'},
                    'writeinterval': 'inherit'}
        if name is not None:
            desc['name'] = name
        return self.create(cik, 'client', desc)

    def drop(self, cik, rids):
        for rid in rids:
            self.exo.drop(cik, rid, defer=True)

        if self.exo.has_deferred(cik):
            self._raise_for_deferred(self.exo.send_deferred(cik))

    def map(self, cik, rid, alias):
        '''Creates an alias for rid. '''
        isok, response = self.exo.map(cik, rid, alias)
        self._raise_for_response(isok, response)
        return response

    def unmap(self, cik, alias):
        '''Removes an alias a child of calling client.'''
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

    def _listing_with_info(self, cik, types, options={}):
        '''Return a list of dicts for each type containing mappings between rids and
        info for that RID. E.g.:
        [{'<rid0>':<info0>, '<rid1>':<info1>}, {'<rid2>':<info2>}, [], {'<rid3>': <info3>}]'''

        assert(len(types) > 0)

        listing = self._exomult(cik,
                                [['listing', types]])[0]

        # listing is a list of lists per type, like: [['<rid0>', '<rid1>'], ['<rid2>'], [], ['<rid3>']]

        # request info for each rid
        # (rids is a flattened version of listing)
        rids = list(itertools.chain(*listing))
        responses = self._exomult(cik, [['info', rid, options] for rid in rids])

        # From the return values make a list of dicts like this:
        # [{'<rid0>':<info0>, '<rid1>':<info1>}, {'<rid2>':<info2>}, [], {'<rid3>': <info3>}]
        # use ordered dicts in case someone cares about order in the output (?)
        response_index = 0
        listing_with_info = []
        for type_list in listing:
            type_response = OrderedDict()
            for rid in type_list:
                type_response[rid] = responses[response_index]
                response_index += 1
            listing_with_info.append(type_response)

        return listing_with_info

    def info(self,
             cik,
             rid={'alias': ''},
             #options={"usage": False, "counts": False},
             options={},
             cikonly=False,
             recursive=False):
        '''Returns info for RID as a dict.'''
        if recursive:
            rid = None if type(rid) is dict else rid
            response = self._infotree(cik, rid=rid, options=options)
        else:
            isok, response = self.exo.info(cik, rid, options)
            self._raise_for_response(isok, response)
        if cikonly:
            if not 'key' in response:
                raise ExoException('{0} has no CIK'.format(rid))
            return response['key']
        else:
            return response

    def flush(self, cik, rids):
        for rid in rids:
            self.exo.flush(cik, rid, defer=True)
        if self.exo.has_deferred(cik):
            self._raise_for_deferred(self.exo.send_deferred(cik))

    def usage(self, cik, rid, metrics, start, end):
        for metric in metrics:
            self.exo.usage(cik, rid, metric, start, end, defer=True)
        responses = []
        if self.exo.has_deferred(cik):
            responses = self._raise_for_deferred(self.exo.send_deferred(cik))
        # show report
        maxlen = max([len(m) for m in metrics])
        for i, r in enumerate(responses):
            print("{0}:{1} {2}".format(
                  metrics[i], ' ' * (maxlen - len(metrics[i])), r))

    def _print_node(self, rid, info, aliases, cli_args, spacer, islast, max_name):
        typ = info['basic']['type']
        if typ == 'client':
            id = 'cik: ' + info['key']
        else:
            id = 'rid: ' + rid
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
        try:
            # show portals metadata if present
            # http://developers.exosite.com/display/POR/Developing+for+Portals
            meta = json.loads(info['description']['meta'])
            device = meta['device']
            if device['type'] == 'vendor':
                add_opt(True, 'vendor', device['vendor'])
                add_opt(True, 'model', device['model'])
                add_opt(True, 'sn', device['sn'])
        except:
            pass

        has_alias = aliases is not None and len(aliases) > 0
        if has_alias:
            add_opt(True, 'aliases', str(aliases))
        # show RID for clients with no alias, or if --verbose was passed
        ridopt = False
        if typ == 'client':
            if has_alias:
                ridopt = '--verbose'
            else:
                ridopt = True
        add_opt(ridopt, 'rid', rid)
        add_opt('--verbose', 'unit', units)
        if 'storage' in info and 'count' in info['storage']:
            add_opt(True, 'count', info['storage']['count'])

        if 'format' in info['description']:
            desc = info['description']['format'] + ' ' + typ + ' ' + id
        else:
            desc = typ + ' ' + id

        print(u'{0}{1}{2} {3} {4}'.format(
            spacer,
            name,
            ' ' * (max_name - len(name)),
            desc,
            u'' if len(opt) == 0 else u'({0})'.format(u', '.join(
                [u'{0}: {1}'.format(k, v) for k, v in opt.iteritems()]))))

    def tree(self, cik, aliases=None, cli_args={}, spacer=u'', level=0, info_options={}):
        '''Print a tree of entities in OneP'''
        max_level = int(cli_args['--level'])
        # print root node
        isroot = len(spacer) == 0
        if isroot:
            # usage and counts are slow, so omit them if we don't need them
            exclude = ['usage']
            if not cli_args['--counts']:
                exclude.append('counts')
                exclude.append('storage')
            info_options = self.make_info_options(exclude=exclude)
            #pprint(info_options)
            # todo: combine these (maybe also the _listing_with_info function
            # below?)
            rid = self.lookup(cik, "")
            info = self.info(cik, options=info_options)
            # info doesn't contain key
            info['key'] = cik
            aliases = info['aliases']
            root_aliases = '(see parent)'
            # todo: can I get aliases for cik? For now, pass []
            self._print_node(rid,
                             info,
                             root_aliases,
                             cli_args,
                             spacer,
                             True,
                             len(info['description']['name']))
            if max_level == 0:
                return
            level += 1

        types = ['dataport', 'datarule', 'dispatch', 'client']
        try:
            listing = self._listing_with_info(cik, types=types, options=info_options)
            # listing(): [['<rid0>', '<rid1>'], ['<rid2>'], [], ['<rid3>']]
            # _listing_with_info(): [{'<rid0>':<info0>, '<rid1>':<info1>},
            #                       {'<rid2>':<info2>}, [], {'<rid3>': <info3>}]
        except pyonep.exceptions.OnePlatformException:
            print(spacer + u"  └─listing for {0} failed. Is info['basic']['status'] == 'expired'?".format(cik))
        else:
            # calculate the maximum length name of all children
            lengths = [len(l[1]['description']['name']) for i in range(len(types)) for l in listing[i].iteritems()]
            max_name = 0 if len(lengths) == 0 else max(lengths)

            # print everything
            for t_idx, t in enumerate(types):
                typelisting = OrderedDict(sorted(listing[t_idx].iteritems(), key=lambda x: x[1]['description']['name'].lower()))
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
                        self._print_node(rid, info, aliases, cli_args, own_spacer, islast, max_name)
                        if max_level == -1 or level < max_level:
                            self.tree(next_cik, info['aliases'], cli_args, child_spacer, level=level + 1, info_options=info_options)
                    else:
                        self._print_node(rid, info, aliases, cli_args, own_spacer, islast, max_name)

    def _uberlistingtree(self, cik, rid=None, stats={'calls': 0}):
        '''Get something like this: {'rid': '<rid1>',
                                     'type': 'client',
                                     'children': [{'rid': '<rid2>',
                                                   'type': 'dataport'}]}'''
        types = ['client', 'dataport', 'datarule', 'dispatch']
        # result tree
        tree = {}
        # generation 0 (self)
        if rid is None:
            rid, listing = self._exomult(cik, [['lookup', 'aliased', ''],
                                               ['listing', types]])
            stats['calls'] += 1
        else:
            # connect_as() is an awkward API. What advantage does it have
            # over passing in an auth dict?
            self.exo.connect_as(rid)
            listing = self._exomult(cik, [['listing', types]])[0]
            stats['calls'] += 1
            self.exo.connect_as(None)

        tree['rid'] = rid

        # children should look like this:
        # [{'type': 'client',
        #   'rid': '<rid1>'},
        #  {'type': 'dataport',
        #   'rid': '<rid2>'}]
        def children(listing):
            return [{'type': type, 'rid': rid} for i, type in enumerate(types) for rid in listing[i]]
        tree['children'] = children(listing)

        for node in tree['children']:
            if node['type'] == 'client':
                subtree = self._uberlistingtree(cik, node['rid'], stats)
                if 'children' not in node:
                    node['children'] = []
                node['children'] = subtree['children']

        return tree


    def _uberinfotree(self, cik):
        '''Get all info for a cik and its children in a nested dict.
        The basic unit is {'rid': '<rid>',
                           'info': <info>,
                           'children': {'client': [child1],
                                        'dataport': [child2]}
                                        }
        where <info-with-children> is just the info object for that node
        with the addition of 'children' key, which is a dict containing
        more nodes. Here's an example return value:

           {'rid': '<rid 0>',
            'info': {'description': ...,
                     'basic': ....,
                     ...},
            'children: [{'rid': '<rid 1>',
                         'info': {'description': ...,
                                  'basic': ...},
                         'children': [{'rid': '<rid 2>',
                                       'info': {'description': ...,
                                                'basic': ...},
                                       'children: [] } } },
                                      {'rid': '<rid 3>',
                                       'info': {'description': ...,
                                                'basic': ...},
                                       'children': {} } }] } }

           As it's building this nested dict, it calls nodeidfn with the rid and info
           (w/o children) for each node.
        '''
        types = ['client', 'dataport', 'datarule', 'dispatch']

        # result tree
        tree = {}

        # list of result nodes to fill out in the next generation
        nextgen = []

        # generation 0 (self)
        rid, listing = self._exomult(cik, [['lookup', 'aliased', ''],
                                           ['listing', types]])

        tree['rid'] = rid

        # children should look like this:
        # [{'type': 'client',
        #   'rid': '<rid1>'},
        #  {'type': 'dataport',
        #   'rid': '<rid2>'}]
        def children(listing):
            return [{'type': type, 'rid': rid} for i, type in enumerate(types) for rid in listing[i]]
        tree['children'] = children(listing)

        # calculate next generation list
        # TODO: paging
        nextgen = tree['children']

        while len(nextgen) > 0:
            print(len(nextgen))
            curgen = nextgen
            nextgen = []

            cmds = []
            for node in curgen:
                if node['type'] == 'client':
                    cmds.append(['listing', types])

            if len(cmds) > 0:
                result = self._exomult(cik, cmds)
            else:
                break

            result_idx = 0
            for i, node in enumerate(curgen):
                # TODO: add results to members of curgen, and update nextgen
                if node['type'] == 'client':
                    r = result[result_idx]
                    node['children'] = children(r)
                    result_idx += 1
                    nextgen.extend(node['children'])

        return tree

    def ubertree(self, cik):
        #pprint(self._uberinfotree(cik)) #, options={'key': True, 'basic': True}))
        stats = {'calls': 0}
        pprint(self._uberlistingtree(cik, rid=None, stats=stats)) #, options={'key': True, 'basic': True}))
        print('calls: {0}'.format(stats['calls']))

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
        listing = self._listing_with_info(cik, types)
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
                print("New script RID: {0}".format(rid))
            else:
                #print('cik: {0} desc: {1}'.format(cik, json.dumps(desc)))
                raise ExoException("Error creating datarule: {0}".format(rid))
            success, rid = self.exo.map(cik, rid, name)
            if success:
                print("Aliased script to: {0}".format(name))
            else:
                raise ExoException("Error aliasing script")
        else:
            success = self.exo.update(cik, rid, desc)
            if success:
                print ("Updated script RID: {0}".format(rid))
            else:
                raise ExoException("Error updating datarule.")

    def cik_recursive(self, cik, fn):
        '''Run fn on cik and all its client children'''
        fn(cik)
        lwi = self._listing_with_info(cik,
                                      ['client'],
                                      {'key': True})
        # [{'<rid0>':<info0>, '<rid1>':<info1>}]
        for rid in lwi[0]:
            self.cik_recursive(lwi[0][rid]['key'], fn)

    def upload_script(self,
                      ciks,
                      filename,
                      name=None,
                      recursive=False,
                      create=False,
                      filterfn=lambda script: script):
        try:
            f = open(filename)
        except IOError:
            raise ExoException('Error opening file {0}.'.format(filename))
        else:
            with f:
                text = filterfn(f.read())
                if name is None:
                    # if no name is specified, use the file name as a name
                    name = os.path.basename(filename)
                for cik in ciks:
                    def up(cik):
                        rid = self._lookup_rid_by_name(cik, name)
                        if rid is not None or create:
                            self._upload_script(cik, name, text, rid=rid)
                        else:
                            print("Skipping CIK: {0} -- {1} not found".format(cik, name))
                            if not create:
                                    print('Pass --create to create it')


                    if recursive:
                        self.cik_recursive(cik, up)
                    else:
                        up(cik)

    def lookup_rid(self, cik, cik_to_find):
        isok, listing = self.exo.listing(cik, types=['client'])
        self._raise_for_response(isok, listing)

        for rid in listing[0]:
            self.exo.info(cik, rid, {'key': True}, defer=True)

        if self.exo.has_deferred(cik):
            responses = self.exo.send_deferred(cik)
            for idx, r in enumerate(responses):
                call, isok, response = r
                self._raise_for_response(isok, response)

                if response['key'] == cik_to_find:
                    return listing[0][idx]

    def record_backdate(self, cik, rid, interval_seconds, values):
        '''Record a list of values and record them as if they happened in
        the past interval_seconds apart. For example, if values
            ['a', 'b', 'c']
        are passed in with interval 10, they're recorded as
            [[0, 'c'], [-10, 'b'], [-20, 'a']].
        interval_seconds must be positive.'''
        timestamp = -interval_seconds

        tvalues = []
        values.reverse()
        for v in values:
            tvalues.append([timestamp, v])
            timestamp -= interval_seconds
        return self.record(cik, rid, tvalues)


    def _create_from_infotree(self, parentcik, infotree):
        '''Create a copy of infotree under parentcik'''
        info_to_copy = infotree['info']
        typ = info_to_copy['basic']['type']
        rid = self.create(parentcik, typ, info_to_copy['description'])
        if 'comments' in info_to_copy and len(info_to_copy['comments']) > 0:
            commands = [['comment', rid, c[0], c[1]] for c in info_to_copy['comments']]
            self._exomult(parentcik, commands)
        if typ == 'client':
            # look up new CIK
            cik = self.info(parentcik, rid)['key']
            children = infotree['info']['children']
            aliases_to_create = {}
            for child in children:
                newrid, _ = self._create_from_infotree(cik, child)
                if child['rid'] in infotree['info']['aliases']:
                    aliases_to_create[newrid] = infotree['info']['aliases'][child['rid']]

            # add aliases in one request
            self._exomult(
                cik,
                list(itertools.chain(*[[['map', r, alias]
                                     for alias in aliases_to_create[r]]
                                     for r in aliases_to_create])))
            return rid, cik
        else:
            return rid, None

    def _counttypes(self, infotree, counts=defaultdict(int)):
        '''Return a dictionary with the count of each type of resource in the
        tree. For example, {'client': 2, 'dataport': 1, 'dispatch':1}'''
        info = infotree['info']
        counts[info['basic']['type']] += 1
        if 'children' in info:
            for child in info['children']:
                counts = self._counttypes(child, counts=counts)
        return counts

    def copy(self, cik, destcik, infotree=None):
        '''Make a copy of cik and its non-client children to destcik and
        return the cik of the copy.'''

        # read in the whole client to copy at once
        if infotree is None:
            destcik = self.lookup_shortcut(destcik)
            infotree = self._infotree(cik, options={})

        # check counts
        counts = self._counttypes(infotree)
        destinfo = self.info(destcik, options={'description': True, 'counts': True})

        noroom = ''
        for typ in counts:
            destlimit = destinfo['description']['limits'][typ]
            destcount = destinfo['counts'][typ]
            needs = counts[typ]
            # TODO: need a way to check if limit is set to 'inherit'
            if type(destlimit) is int and destlimit - destcount < needs:
                noroom = noroom + 'Thing to copy has {0} {1}{4}, parent has limit of {3} (and is using {2}).\n'.format(
                    needs, typ, destcount, destlimit, 's' if needs > 1 else '')

        if len(noroom) > 0:
            raise ExoException('Copy would violate parent limits:\n{0}'.format(noroom))

        cprid, cpcik = self._create_from_infotree(destcik, infotree)

        return cprid, cpcik

    def _remove(self, dct, keypaths):
        '''Remove keypaths from dictionary.
        >>> ex = ExoRPC()
        >>> ex._remove({'a': {'b': {'c': 1}}}, [['a', 'b', 'c']])
        {'a': {'b': {}}}
        >>> ex._remove({'a': {'b': {'q': 1}}}, [['a', 'b', 'c']])
        {'a': {'b': {'q': 1}}}
        >>> ex._remove({}, [['a'], ['b'], ['c']])
        {}
        >>> ex._remove({'q': 'a'}, [['a'], ['b']])
        {'q': 'a'}
        '''
        for kp in keypaths:
            x = dct
            for i, k in enumerate(kp):
                if k in x:
                    if i == len(kp) - 1:
                        del x[k]
                    else:
                        x = x[k]
                else:
                    break
        return dct

    def _differences(self, dict1, dict2):
        import difflib
        differ = difflib.Differ()

        s1 = json.dumps(dict1, indent=2, sort_keys=True).splitlines(1)
        s2 = json.dumps(dict2, indent=2, sort_keys=True).splitlines(1)

        return list(differ.compare(s1, s2))

    def _infotree(self, cik, rid=None, nodeidfn=lambda rid, info: rid, options={}):
        '''Get all info for a cik and its children in a nested dict.
        The basic unit is {'rid': '<rid>', 'info': <info-with-children>},
        where <info-with-children> is just the info object for that node
        with the addition of 'children' key, which is a dict containing
        more nodes. Here's an example return value:

           {'rid': '<rid 0>', 'info': {'description': ...,
                        'basic': ....,
                        ...
                        'children: [{'rid': '<rid 1>', 'info': {'description': ...,
                                                'basic': ...
                                                'children': [{'rid': '<rid 2>', 'info': {'description': ...,
                                                                         'basic': ...,
                                                                         'children: [] } } },
                                    {'rid': '<rid 3>', 'info': {'description': ...,
                                                'basic': ...
                                                'children': {} } }] } }

           As it's building this nested dict, it calls nodeidfn with the rid and info
           (w/o children) for each node.
        '''
        types = ['client', 'dataport', 'datarule', 'dispatch']
        #print(cik, rid)
        # TODO: make exactly one HTTP request per node
        listing = []
        norid = rid is None
        if norid:
            rid = self._exomult(cik, [['lookup', 'aliased', '']])[0]

        info = self._exomult(cik, [['info', rid, options]])[0]

        if norid or info['basic']['type'] == 'client':
            if not norid:
                # key is only available to owner (not the resource itself)
                cik = info['key']
            listing = self._exomult(cik,
                                    [['listing', types]])[0]

        myid = nodeidfn(rid, info)

        info['children'] = []
        for typ, ridlist in zip(types, listing):
            for childrid in ridlist:
                tr = self._infotree(cik, childrid, nodeidfn=nodeidfn, options=options)
                info['children'].append(tr)
        info['children'].sort(key=itemgetter('rid'))

        return {'rid': myid, 'info': info}

    def _difffilter(self, difflines):
        d = difflines

        # TODO: fix this for new infotree format

        # replace differing rid children lines with a single <<rid>>
        ridline = '^[+-](.*").*\.[a-f0-9]{40}(".*)\n'
        d = re.sub(ridline * 2, r' \1<<RID>>\2\n', d, flags=re.MULTILINE)

        # replace differing rid alias lines with a single <<rid>> placeholder
        a = '(.*")[a-f0-9]{40}("\: \[)\n'
        plusa = '^\+' + a
        minusa = '^\-' + a
        d = re.sub(plusa + minusa, r' \1<<RID>>\2\n', d, flags=re.MULTILINE)
        d = re.sub(minusa + plusa, r' \1<<RID>>\2\n', d, flags=re.MULTILINE)

        # replace differing cik lines with a single <<cik>> placeholder
        a = '(.*"key"\: ")[a-f0-9]{40}(",.*)\n'
        plusa = '^\+' + a
        minusa = '^\-' + a
        d = re.sub(plusa + minusa, r' \1<<CIK>>\2\n', d, flags=re.MULTILINE)
        d = re.sub(minusa + plusa, r' \1<<CIK>>\2\n', d, flags=re.MULTILINE)

        return d

    def diff(self, cik1, cik2, full=False, nochildren=False):
        '''Show differences between two ciks.'''

        cik2 = self.lookup_shortcut(cik2)

        # list of info "keypaths" to not include in comparison
        # only the last item in the list is removed. E.g. for a
        # keypath of ['counts', 'disk'], only the 'disk' key is
        # ignored.
        ignore = [['usage'],
                  ['counts', 'disk'],
                  ['counts', 'email'],
                  ['counts', 'http'],
                  ['counts', 'share'],
                  ['counts', 'sms'],
                  ['counts', 'xmpp'],
                  ['basic', 'status'],
                  ['basic', 'modified'],
                  ['basic', 'activity'],
                  ['data'],
                  ['storage']]

        if nochildren:
            info1 = self.info(cik1)
            info1 = self._remove(info1, ignore)
            info2 = self.info(cik2)
            info2 = self._remove(info2, ignore)
        else:
            def name_prepend(rid, info):
                if not full:
                    self._remove(info, ignore)
                # prepend the name so that node names tend to sort (and so
                # compare well)
                return info['description']['name'] + '.' + rid
            info1 = self._infotree(cik1, nodeidfn=name_prepend, options={})
            info2 = self._infotree(cik2, nodeidfn=name_prepend, options={})

        if info1 == info2:
            return None
        else:
            differences = self._differences(info1, info2)
            differences = ''.join(differences)

            if not full:
                # pass through a filter that removes
                # differences that we don't care about
                # (e.g. different RIDs)
                differences = self._difffilter(differences)

                if all([line[0] == ' ' for line in differences.split('\n')]):
                    return None

            return differences

    def make_info_options(self, include=[], exclude=[]):
        '''Create options for the info command based on included
        and excluded keys.'''
        options = {}
        # TODO: this is a workaround. The RPC API returns empty list if any
        # keys are set to false. So, the workaround is to include all keys
        # except for the excluded ones. This has the undesirable
        # side-effect of producing "<key>": null in the results, so it would be
        # better for this to be done in the API.
        #
        #for key in exclude:
        #    options[key] = False

        if len(exclude) > 0:
            options.update(dict([(k, True) for k in ['aliases',
                                                        'basic',
                                                        'counts',
                                                        'description',
                                                        'key',
                                                        'shares',
                                                        'storage',
                                                        'subscribers',
                                                        'tags',
                                                        'usage']
                                    if k not in exclude]))
        else:
            for key in include:
                options[key] = True

        return options


class ExoData():
    '''Implements the Data Interface API
    https://github.com/exosite/api/tree/master/data'''

    def __init__(self, url='http://m2.exosite.com'):
        self.url = url

    def raise_for_status(self, r):
        try:
            r.raise_for_status()
        except Exception as ex:
            raise ExoException(str(ex))

    def read(self, cik, aliases):
        headers = {'X-Exosite-CIK': cik,
                   'Accept': 'application/x-www-form-urlencoded; charset=utf-8'}
        url = self.url + '/onep:v1/stack/alias?' + '&'.join(aliases)
        r = requests.get(url, headers=headers)
        self.raise_for_status(r)
        return r.text

    def write(self, cik, alias_values):
        headers = {'X-Exosite-CIK': cik,
                   'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'}
        url = self.url + '/onep:v1/stack/alias'
        data = '&'.join(['='.join(t) for t in alias_values])
        r = requests.post(url, headers=headers, data=data)
        self.raise_for_status(r)
        return r.text

    def writeread(self, cik, alias_values, aliases):
        headers = {'X-Exosite-CIK': cik,
                   'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
                   'Accept': 'application/x-www-form-urlencoded; charset=utf-8'}
        url = self.url + '/onep:v1/stack/alias?' + '&'.join(aliases)
        data = '&'.join(['='.join(t) for t in alias_values])
        r = requests.post(url, headers=headers, data=data)
        self.raise_for_status(r)
        return r.text

    def ip(self):
        r = requests.get(self.url + '/ip')
        r.raise_for_status()
        return r.text


def parse_ts(s):
    return int(time.mktime(parser.parse(s).timetuple()))

def is_ts(s):
    return re.match('^[0-9]+$', s) is not None

def get_startend(args):
    '''Get start and end timestamps based on standard arguments'''
    start = args.get('--start', None)
    end = args.get('--end', None)
    if start is None:
        start = 1
    elif is_ts(start):
        start = int(start)
    else:
        start = parse_ts(start)
    if end is None or end == 'now':
        end = int(time.mktime(datetime.now().timetuple()))
    elif is_ts(end):
        end = int(end)
    else:
        end = parse_ts(end)
    return start, end

def format_time(sec):
    '''Formats a time interval for human consumption'''
    intervals = [[60 * 60 * 24, 'd'],
                    [60 * 60, 'h'],
                    [60, 'm']]
    text = ""
    for s, label in intervals:
        if sec >= s and sec / s > 0:
            text = "{0} {1}{2}".format(text, sec / s, label)
            sec -= s * (sec / s)
    if sec > 0:
        text += " {0}s".format(sec)
    return text.strip()


def spark(numbers, empty_val=None):
    """Generate a text based sparkline graph from a list of numbers (ints or
    floats).

    When value is empty_val, show no bar.

    https://github.com/1stvamp/py-sparkblocks
        start = args['--start']
        end = args['--end']
        parse_ts = lambda(s): int(time.mktime(parser.parse(s).timetuple()))
        is_ts = lambda(s): re.match('^[0-9]+$', s) is not None
        if is_ts(start):
            start = int(start)
        else:
            start = parse_ts(start)
        if end is None or end == 'now':
            end = int(time.mktime(datetime.now().timetuple()))
        elif is_ts(end):
            end = int(end)
        else:
            end = parse_ts(end)
    Based on:
      https://github.com/holman/spark
    and:
      http://www.datadrivenconsulting.com/2010/06/twitter-sparkline-generator/
    """

    out = []

    min_value = min(numbers)
    max_value = max(numbers)
    value_scale = max_value - min_value

    for number in numbers:
        if number == empty_val:
            out.append(u" ")
        else:
            if (number - min_value) != 0 and value_scale != 0:
                scaled_value = (number - min_value) / value_scale
            else:
                scaled_value = 0
            num = math.floor(min([6, (scaled_value * 7)]))

            # Hack because 9604 and 9608 aren't vertically aligned the same as
            # other block elements
            if num == 3:
                if (scaled_value * 7) < 3.5:
                    num = 2
                else:
                    num = 4
            elif num == 7:
                num = 6

            out.append(unichr(int(9601 + num)))

    return ''.join(out)

def meanstdv(l):
    '''Calculate mean and standard deviation'''
    n, mean, std = len(l), 0, 0
    mean = sum(l) / float(len(l))
    std = math.sqrt(sum([(x - mean)**2 for x in l]) / (len(l) - 1))
    return mean, std


def show_intervals(er, cik, rid, start, end, limit, numstd=None):
    # show a distribution of intervals between data
    data = er.read(cik,
                   rid,
                   limit,
                   sort='desc',
                   starttime=start,
                   endtime=end)

    if len(data) == 0:
        return
    intervals = [data[i - 1][0] - data[i][0] for i in xrange(1, len(data))]
    intervals = sorted(intervals)

    if numstd is not None:
        # only include data within numstd standard deviations
        # of the mean
        mean, std = meanstdv(intervals)
        intervals = [x for x in intervals
                    if mean - numstd * std <= x
                    and x <= mean + numstd * std]
        if len(intervals) == 0:
            return
    num_bins = 60
    min_t, max_t = min(intervals), max(intervals)
    bin_size = float(max_t - min_t) / num_bins * 1.0
    bins = []
    for i in range(num_bins):
        bin_min = min_t + i * bin_size
        bin_max = min_t + (i + 1) * bin_size
        if i != 0:
            critfn = lambda x: bin_min < x and x <= bin_max
        else:
            critfn = lambda x: bin_min <= x and x <= bin_max
        #bins.append((bin_min, bin_max, float(
        #    sum(itertools.imap(critfn, intervals)))))
        bins.append(float(
            sum(itertools.imap(critfn, intervals))))

    if False:
        # debug
        print(bins)
        print(num_bins * bin_size)
        print(bin_size)
        print(min_t)
        print(max_t)
        print(set(intervals))

    print(spark(bins, empty_val=0))

    min_label = format_time(min_t)
    max_label = format_time(max_t)
    sys.stdout.write(min_label)
    sys.stdout.write(' ' * (num_bins - len(min_label) - len(max_label)))
    sys.stdout.write(max_label + '\n')


def read_cmd(er, cik, rids, args):
    '''Read command'''
    limit = args['--limit']
    limit = 1 if limit is None else int(limit)

    # time range
    start, end = get_startend(args)

    timeformat = args['--timeformat']
    headertype = args['--header']
    if headertype == 'name':
        # look up names of rids
        infos = er._exomult(cik,
                            [['info', r, {'description': True}] for r in rids])
        headers = ['timestamp'] + [i['description']['name'] for i in infos]
    else:
        headers = ['timestamp'] + [str(r) for r in args['<rid>']]

    dw = csv.DictWriter(sys.stdout, headers)
    if headertype is not None:
        # write headers
        dw.writerow(dict([(h, h) for h in headers]))

    fmt = args['--format']

    recarriage = re.compile('\r(?!\\n)')

    def printline(timestamp, val):
        if fmt == 'raw':
            print(val[0])
        else:
            if timeformat == 'unix':
                dt = timestamp
            elif timeformat == 'iso8601':
                dt = datetime.isoformat(datetime.fromtimestamp(timestamp))
            else:
                dt = datetime.fromtimestamp(timestamp)

            row = {'timestamp': str(dt)}

            def stripcarriage(s):
                # strip carriage returns not followed
                if type(s) is str:
                    return recarriage.sub('', s)
                else:
                    return s

            values = dict([(str(headers[i + 1]), stripcarriage(val[i])) for i in range(len(rids))])

            row.update(values)
            dw.writerow(row)


    sleep_seconds = 2
    if args['--follow']:
        if len(rids) > 1:
            raise ExoException('--follow does not support reading from multiple rids')
        results = []
        while len(results) == 0:
            results = er.readmult(cik,
                                  rids,
                                  limit=1,
                                  sort='desc')
            # --follow doesn't want the result to be an iterator
            results = list(results)
            if len(results) > 0:
                for last_t, last_v in results:
                    printline(last_t, last_v)
            else:
                time.sleep(sleep_seconds)
        while True:
            results = er.readmult(cik,
                                  rids,
                                  sort='desc',
                                  # Read all points that arrived since last
                                  # read time. Could also be now - last_t?
                                  limit=sleep_seconds * 3,
                                  starttime=last_t + 1)
            results = list(results)
            results.reverse()

            for t, v in results:
                printline(t, v)

            if len(results) > 0:
                last_t, last_v = results[-1]

            time.sleep(sleep_seconds)
    else:
        chunkhours = args['--chunkhours']
        if chunkhours is not None and (start is None or end is None):
            raise ExoException(
                "--chunkhours requires --start and --end be set")
        result = er.readmult(cik,
                                rids,
                                sort=args['--sort'],
                                starttime=start,
                                endtime=end,
                                limit=limit,
                                chunkhours=chunkhours)
        for t, v in result:
            printline(t, v)


def plain_print(arg):
    print(arg)


def pretty_print(arg):
    print(json.dumps(arg, sort_keys=True, indent=4, separators=(',', ': ')))




def handle_args(cmd, args):
    er = ExoRPC(host=args['--host'], port=args['--port'], https=args['--https'], httptimeout=args["--httptimeout"])
    if cmd in ['ip', 'data']:
        if args['--https'] is True or args['--port'] is not None or args['--debughttp'] is True:
            # TODO: support these
            raise ExoException('--https, --port, and --debughttp are not supported for ip and data commands.')
        ed = ExoData(url='http://' + args['--host'])

    if '<cik>' in args:
        cik = args['<cik>']
        if type(cik) is list:
            cik = [er.lookup_shortcut(c) for c in cik]
        else:
            cik = er.lookup_shortcut(cik)
    else:
        # for data ip command
        cik = None
    def rid_or_alias(rid):
        '''Translate what was passed for <rid> to an alias object if
           it doesn't look like a RID.'''
        if er.regex_rid.match(rid) is None:
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
        pr = pretty_print
    else:
        pr = plain_print

    if cmd == 'read':
        read_cmd(er, cik, rids, args)
    elif cmd == 'write':
        er.write(cik, rids[0], args['--value'])
    elif cmd == 'record':
        interval = args['--interval']
        if interval is None:
            entries = []
            # split timestamp, value
            has_errors = False
            if args['-']:
                headers = ['timestamp', 'value']
                dr = csv.DictReader(sys.stdin, headers)
                for row in dr:
                    # TODO: handle something other than unix timestamps
                    entries.append([int(row['timestamp']), row['value']])
            else:
                tvalues = args['--value']
                reentry = re.compile('(-?\d+),(.*)')
                for tv in tvalues:
                    match = reentry.match(tv)
                    if match is None:
                        try:
                            t, v = tv.split(',')
                            t = parse_ts(t)
                            entries.append([t, v])
                        except Exception:
                            sys.stderr.write(
                                'Line not in <timestamp>,<value> format: {0}'.format(tv))
                            has_errors = True
                    else:
                        g = match.groups()
                        # TODO: handle something other than unix timestamps
                        entries.append([int(g[0]), g[1]])

            if has_errors or len(entries) == 0:
                raise ExoException("Problems with input.")
            else:
                er.record(cik, rids[0], entries)
        else:
            if args['-']:
                values = [v.strip() for v in sys.stdin.readlines()]
            else:
                values = args['--value']
            interval = int(interval)
            if interval <= 0:
                raise ExoException("--interval must be positive")
            er.record_backdate(cik, rids[0], interval, values)
    elif cmd == 'create':
        typ = args['--type']
        ridonly = args['--ridonly']
        cikonly = args['--cikonly']
        if ridonly and cikonly:
            raise ExoException('--ridonly and --cikonly are mutually exclusive')
        if args['-']:
            s = sys.stdin.read()
            try:
                desc = json.loads(s)
            except Exception as ex:
                raise ExoException(ex)
            rid = er.create(cik,
                            type=typ,
                            desc=desc,
                            name=args['--name'])
        elif typ == 'client':
            rid = er.create_client(cik,
                                   name=args['--name'])
        elif typ == 'dataport':
            rid = er.create_dataport(cik,
                                     args['--format'],
                                     name=args['--name'])
        else:
            raise ExoException('No defaults for {0}.'.format(args['--type']))
        if ridonly:
            pr(rid)
        elif cikonly:
            print(er.info(cik, rid, cikonly=True))
        else:
            pr('rid: {0}'.format(rid))
            if typ == 'client':
                # for convenience, look up the cik
                print('cik: {0}'.format(er.info(cik, rid, cikonly=True)))
        if args['--alias'] is not None:
            er.map(cik, rid, args['--alias'])
            if not ridonly:
                print("alias: {0}".format(args['--alias']))
    elif cmd == 'update':
        s = sys.stdin.read()
        try:
            desc = json.loads(s)
        except Exception as ex:
            raise ExoException(ex)
        pr(er.update(cik, rids[0], desc=desc))
    elif cmd == 'map':
        er.map(cik, rids[0], args['<alias>'])
    elif cmd == 'unmap':
        er.unmap(cik, args['<alias>'])
    elif cmd == 'lookup':
        # look up by cik or alias
        cik_to_find = args['--cik']
        if cik_to_find is not None:
            cik_to_find = er.lookup_shortcut(cik_to_find)
            rid = er.lookup_rid(cik, cik_to_find)
            if rid is not None:
                pr(rid)
        else:
            alias = args['<alias>']
            if alias is None:
                alias = ""
            pr(er.lookup(cik, alias))
    elif cmd == 'drop':
        if args['--all-children']:
            er.drop_all_children(cik)
        else:
            if len(rids) == 0:
                raise ExoException("<rid> is required")
            er.drop(cik, rids)
    elif cmd == 'listing':
        types = args['--type']
        if len(types) == 0:
            types = ['client', 'dataport', 'datarule', 'dispatch']
        listing = er.listing(cik, types)
        if args['--plain']:
            for l in listing:
                for rid in listing[0]:
                    print(rid)
        else:
            pr(listing)
    elif cmd == 'info':
        include = args['--include']
        include = [] if include is None else [key.strip()
                                              for key in include.split(',')]
        exclude = args['--exclude']
        exclude = [] if exclude is None else [key.strip()
                                              for key in exclude.split(',')]

        options = er.make_info_options(include, exclude)
        info = er.info(cik,
                       rids[0],
                       options=options,
                       cikonly=args['--cikonly'],
                       recursive=args['--recursive'])
        if args['--pretty']:
            pr(info)
        else:
            # output json
            pr(json.dumps(info))
    elif cmd == 'flush':
        er.flush(cik, rids)
    elif cmd == 'usage':
        allmetrics = ['client',
                      'dataport',
                      'datarule',
                      'dispatch',
                      'email',
                      'http',
                      'sms',
                      'xmpp']

        start, end = get_startend(args)
        er.usage(cik, rids[0], allmetrics, start, end)
    # special commands
    elif cmd == 'tree':
        er.tree(cik, cli_args=args)
    elif cmd == 'ut':
        er.ubertree(cik)
    elif cmd == 'script':
        # cik is a list of ciks
        er.upload_script(cik, args['<script-file>'],
                         name=args['--name'],
                         recursive=args['--recursive'],
                         create=args['--create'])
    elif cmd == 'spark':
        days = int(args['--days'])
        end = time.mktime(datetime.now().timetuple())
        start = time.mktime((datetime.now() - timedelta(days=days)).timetuple())
        numstd = args['--stddev']
        numstd = int(numstd) if numstd is not None else None
        show_intervals(er, cik, rids[0], start, end, limit=1000000, numstd=numstd)
    elif cmd == 'copy':
        destcik = args['<destination-cik>']
        newrid, newcik = er.copy(cik, destcik)
        if args['--cikonly']:
            pr(newcik)
        else:
            pr('cik: ' + newcik)
    elif cmd == 'diff':
        if sys.version_info < (2, 7):
            raise ExoException('diff command requires Python 2.7 or above')

        diffs = er.diff(cik,
                        args['<cik2>'],
                        full=args['--full'],
                        nochildren=args['--no-children'])
        if diffs is not None:
            print(diffs)
    elif cmd == 'ip':
        pr(ed.ip())
    elif cmd == 'data':
        reads = args['--read']
        writes = args['--write']
        def get_alias_values(writes):
            # TODO: support values with commas
            alias_values = []
            re_assign = re.compile('(.*),(.*)')
            for w in writes:
                if w.count(',') > 1:
                    raise ExoException('Values with commas not supported yet.')
                m = re_assign.match(w)
                if m is None or len(m.groups()) != 2:
                    raise ExoException("Bad alias assignment format")
                alias_values.append(m.groups())
            return alias_values

        if len(reads) > 0 and len(writes) > 0:
            alias_values = get_alias_values(writes)
            print(ed.writeread(cik, alias_values, reads))
        elif len(reads) > 0:
            print(ed.read(cik, reads))
        elif len(writes) > 0:
            alias_values = get_alias_values(writes)
            ed.write(cik, alias_values)
    else:
        # search plugins
        handled = False
        for plugin in plugins:
            if cmd in plugin.command():
                options = {'cik': cik, 'rpc': er}
                try:
                    options['data'] = ed
                except NameError:
                    # no problem
                    pass
                plugin.run(cmd, args, options)
                handled = True
                break
        if not handled:
            raise ExoException("Command not handled")


class DiscreetFilter(object):
    '''Filter stdin/stdout to hide anything that looks like
       an RID'''
    def __init__(self, out):
        self.out = out
        self.ridre = re.compile('([a-fA-F0-9]{20})([a-fA-F0-9]{20})')

    def write(self, message):
        self.out.write(self.ridre.sub(r'\g<1>01234567890123456789',
                                      message))

def cmd(argv=None, stdin=None, stdout=None, stderr=None):
    '''Wrap the command line interface. Globally redirects args
    and io so that the application can be tested externally.'''

    # globally redirect args and io
    if argv is not None:
        sys.argv = argv
    if stdin is not None:
        sys.stdin = stdin
    if stderr is not None:
        sys.stderr = stderr
    if stdout is not None:
        sys.stdout = stdout

    command_list = '  '.join([k + '\n' for k in cmd_doc])
    doc = __doc__.replace('{{ command_list }}', command_list)
    args = docopt(
        doc,
        version="Exosite Command Line {0}".format(__version__),
        options_first=True)

    # get command args
    cmd = args['<command>']
    argv = [cmd] + args['<args>']
    if cmd in cmd_doc:
        args_cmd = docopt(cmd_doc[cmd], argv=argv)
    else:
        print('Unknown command {0}. Try "exo --help"'.format(cmd))
        return 1
    # merge command-specific arguments into general arguments
    args.update(args_cmd)
    # turn on stdout/stderr filtering
    if args['--discreet']:
        sys.stdout = DiscreetFilter(sys.stdout)
        sys.stderr = DiscreetFilter(sys.stderr)

    # configure logging
    logging.basicConfig(stream=sys.stderr)
    logging.getLogger("pyonep.onep").setLevel(logging.ERROR)
    if args['--debughttp']:
        # TODO: log debug level messages to stdout
        logging.getLogger("pyonep.onep").setLevel(logging.DEBUG)

    # substitute environment variables
    if args['--host'] is None:
        args['--host'] = os.environ.get('EXO_HOST', DEFAULT_HOST)
    if args['--port'] is None:
        args['--port'] = os.environ.get('EXO_PORT', None)

    try:
        handle_args(cmd, args)
    except ExoException as ex:
        # command line tool threw an exception on purpose
        sys.stderr.write("Command line error: {0}\r\n".format(ex))
        return 1
    except ExoRPC.RPCException as ex:
        # pyonep library call signaled an error in return values
        sys.stderr.write("One Platform error: {0}\r\n".format(ex))
        return 1
    except pyonep.exceptions.OnePlatformException as ex:
        # pyonep library call threw an exception on purpose
        sys.stderr.write("One Platform exception: {0}\r\n".format(ex))
        return 1
    except pyonep.exceptions.JsonRPCRequestException as ex:
        sys.stderr.write("JSON RPC Request Exception: {0}\r\n".format(ex))
        return 1
    except pyonep.exceptions.JsonRPCResponseException as ex:
        sys.stderr.write("JSON RPC Response Exception: {0}\r\n".format(ex))
        return 1
    except KeyboardInterrupt:
        if args['--debug']:
            raise
    return 0


class CmdResult():
    def __init__(self, exitcode, stdout, stderr):
        self.exitcode = exitcode
        self.stdout = stdout
        self.stderr = stderr


def run(argv, stdin):
    '''Runs an exoline command, translating stdin from
    string and stdout to string. Returns a CmdResult.'''
    if type(stdin) is str:
        sio = StringIO.StringIO()
        sio.write(stdin)
        sio.seek(0)
        stdin = sio
    stdout = StringIO.StringIO()
    stderr = StringIO.StringIO()

    # unicode causes problems in docopt
    argv = [str(a) for a in argv]
    exitcode = cmd(argv=argv, stdin=stdin, stdout=stdout, stderr=stderr)
    stdout.seek(0)
    stdout = stdout.read().strip()  # strip to get rid of leading newline
    stderr.seek(0)
    stderr = stderr.read().strip()
    return CmdResult(exitcode, stdout, stderr)


if __name__ == '__main__':
    sys.exit(cmd(sys.argv))
