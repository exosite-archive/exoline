#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Exoline - Exosite IoT Command Line Interface
https://github.com/exosite/exoline

Usage:
  exo [--help] [options] <command> [<args> ...]

Commands:
{{ command_list }}
Options:
  --host=<host>          OneP host. Default is $EXO_HOST or m2.exosite.com
  --port=<port>          OneP port. Default is $EXO_PORT or 443
  -c --config=<file>     Config file [default: ~/.exoline]
  --httptimeout=<sec>    HTTP timeout [default: 60] (default for copy is 480)
  --https                Enable HTTPS (deprecated, HTTPS is default)
  --http                 Disable HTTPS
  --useragent=<ua>       Set User-Agent Header for outgoing requests
  --debug                Show debug info (stack traces on exceptions)
  -d --debughttp         Turn on debug level logging in pyonep
  --curl                 Show curl calls for requests. Implies --debughttp
  --discreet             Obfuscate RIDs in stdout and stderr
  -e --clearcache        Invalidate Portals cache after running command
  --portals=<server>     Portals server [default: https://portals.exosite.com]
  -t --vendortoken=<vt>  Vendor token (/admin/home in Portals)
  -n --vendor=<vendor>   Vendor identifier (/admin/managemodels in Portals)
			 (See http://github.com/exosite/exoline#provisioning)
  -h --help              Show this screen
  -v --version           Show version

See 'exo <command> --help' for more information on a specific command.
"""

# Copyright (c) 2014, Exosite, LLC
# All rights reserved
from __future__ import unicode_literals
import sys
import os
from os.path import expanduser
import json
if sys.version_info < (3, 0):
    import unicodecsv as csv
else:
    import csv
import platform
import re
from datetime import datetime
from datetime import timedelta
import time
from pprint import pprint
from operator import itemgetter
import logging
from collections import defaultdict
import copy
import difflib

import six
from six import BytesIO
from six import StringIO
from six import iteritems

import pytz
# python 2.6 support
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
import itertools
import math
import glob

from docopt import docopt
from dateutil import parser
import requests
import yaml
import importlib

from pyonep import onep
from pyonep import provision
import pyonep

try:
    from ..exoline import timezone
except:
    from exoline import timezone

try:
    from ..exoline import __version__
    from ..exoline.exocommon import ExoException
except:
    from exoline import __version__
    from exoline.exocommon import ExoException

DEFAULT_HOST = 'm2.exosite.com'
DEFAULT_PORT = '80'
DEFAULT_PORT_HTTPS = '443'

PERF_DATA = []

cmd_doc = OrderedDict([
    ('read',
        '''Read data from a resource.\n\nUsage:
    exo [options] read <cik> [<rid> ...]

Command options:
    --follow                 continue reading (ignores --end)
    --limit=<limit>          number of data points to read [default: 1]
    --start=<time>
    --end=<time>             start and end times (see details below)
    --tz=<TZ>                Olson TZ name
    --sort=<order>           asc or desc [default: desc]
    --selection=all|autowindow|givenwindow  downsample method [default: all]
    --format=csv|raw         output format [default: csv]
    --timeformat=unix|human|iso8601|excel
                             unix timestamp, human-readable, or spreadsheet-
                             compatible? [default: human]
    --header=name|rid        include a header row
    --chunksize=<size>       [default: 212] break read into requests of
                             length <size>, printing data as it is received.
    {{ helpoption }}

    If <rid> is omitted, reads all datasources and datarules under <cik>.
    All output is in UTC.

    {{ startend }}'''),
    ('write',
        '''Write data at the current time.\n\nUsage:
    exo [options] write <cik> [<rid>] --value=<value>
    exo [options] write <cik> [<rid>] -

The - form takes the value to write from stdin. For example:

    $ echo '42' | exo write 8f21f0189b9acdc82f7ec28dc0c54ccdf8bc5ade myDataport -'''),
    ('record',
        '''Write data at a specified time.\n\nUsage:
    exo [options] record <cik> [<rid>] ((--value=<timestamp,value> ...) | -)
    exo [options] record <cik> [<rid>] --interval=<seconds> ((--value=<value> ...) | -)

    - reads data from stdin. Data should be in CSV format (no headers) with rows
      like this: <unix timestamp>,<value>

Command options:
    --interval generates timestamps at a regular interval into the past.
    --chunksize=<lines>       [default: 212] break record into requests of length <lines>

    '''),
    ('create',
        '''Create a resource from a json description passed on stdin (with -),
    or using command line shorthand (other variants).\n\nUsage:
    exo [options] create <cik> (--type=client|clone|dataport|datarule|dispatch) -
    exo [options] create <cik> --type=client
    exo [options] create <cik> --type=dataport (--format=float|integer|string)

Command options:
    --name=<name     set a resource name (overwriting the one in stdin if present)
    --alias=<alias>  set an alias
    --ridonly        output the RID by itself on a line
    --cikonly        output the CIK by itself on a line (--type=client only)
    {{ helpoption }}

Details:
    Pass - and a json description object on stdin, or leave it off to use defaults.
    Description is documented here:
    https://github.com/exosite/docs/tree/master/rpc#create-client
    https://github.com/exosite/docs/tree/master/rpc#create-dataport
    https://github.com/exosite/docs/tree/master/rpc#create-datarule

    If - is not present, creates a resource with common defaults.'''),
    ('listing',
        '''List the RIDs of a client's children.\n\nUsage:
    exo [options] listing <cik>

Command options:
    --types=<type1>,...  which resource types to list
                         [default: client,dataport,datarule,dispatch]
    --filters=<f1>,...   criteria for which resources to include
                         [default: owned]
                         activated  resources shared with and activated
                                    by client (<cik>)
                         aliased    resources aliased by client (<cik>)
                         owned      resources owned by client (<cik>)
                         public     public resources
    --tagged=<tag1>,...  resources that have been tagged by any client, and
                         that the client (<cik>) has read access to.
    --plain              show only the child RIDs
    --pretty             pretty print output'''),
    ('info',
        '''Get metadata for a resource in json format.\n\nUsage:
    exo [options] info <cik> [<rid>]

Command options:
    --cikonly      print CIK by itself
    --pretty       pretty print output
    --recursive    embed info for any children recursively
    --level=<num>  number of levels to recurse through the client tree
    --include=<key list>
    --exclude=<key list>
                   comma separated list of info keys to include and exclude.
                   Available keys are aliases, basic, counts, description,
                   key, shares, subscribers, tags, usage. If omitted,
                   all available keys are returned.'''),
    ('update',
        '''Update a resource from a json description passed on stdin.\n\nUsage:
    exo [options] update <cik> <rid> -

    For details see https://github.com/exosite/docs/tree/master/rpc#update'''),
    ('map',
        '''Add an alias to a resource.\n\nUsage:
    exo [options] map <cik> <rid> <alias>'''),
    ('unmap',
        '''Remove an alias from a resource.\n\nUsage:
    exo [options] unmap <cik> <alias>'''),
    ('lookup',
        '''Look up a resource's RID based on its alias cik.\n\nUsage:
    exo [options] lookup <cik> [<alias>]
    exo [options] lookup <cik> --owner-of=<rid>
    exo [options] lookup <cik> --share=<code>
    exo [options] lookup <cik> --cik=<cik-to-find>

    If <alias> is omitted, the rid for <cik> is returned. This is equivalent to:
    exo lookup <cik> ""

    The --owner-of variant returns the RID of the immediate parent (owner)
    of <rid>.

    The --share variant returns the RID associated with a share code'''),
    ('drop',
        '''Drop (permanently delete) a resource.\n\nUsage:
    exo [options] drop <cik> [<rid> ...]

Command options:
    --all-children  drop all children of the resource.
    {{ helpoption }}

Warning: if the resource is a client with a serial number
associated with it, the serial number is not released.'''),
    ('flush',
        '''Remove time series data from a resource.\n\nUsage:
    exo [options] flush <cik> [<rid>]

Command options:
    --start=<time>  flush all points newer than <time> (exclusive)
    --end=<time>    flush all points older than <time> (exclusive)

    If --start and --end are both omitted, all points are flushed.'''),
    ('usage',
        '''Display usage of One Platform resources over a time period.\n\nUsage:
    exo [options] usage <cik> [<rid>] --start=<time> [--end=<time>]

    {{ startend }}'''),
    ('tree', '''Display a resource's descendants.\n\nUsage:
    exo [options] tree [--verbose] [--values] <cik>

Command options:
    --level=<num>  depth to traverse, omit or -1 for no limit [default: -1]'''),
    ('twee', '''Display a resource's descendants. Like tree, but more wuvable.\n\nUsage:
    exo [options] twee <cik>

Command options:
    --nocolor      don't use color in output (color is always off in Windows)
    --level=<num>  depth to traverse, omit or -1 for no limit [default: -1]
    --rids         show RIDs instead CIKs below the top level

Example:

    $ exo twee 7893635162b84f78e4475c2d6383645659545344
     Temporary CIK    cl cik: 7893635162b84f78e4475c2d6383645659545344
       ├─  dp.i rid.098f1: 77 (just now)
       └─  dp.s config: {"a":1,"b":2} (21 seconds ago)
    $ exo read 7893635162b84f78e4475c2d6383645659545344 rid.098f1
    2014-09-12 13:48:28-05:00,77
    $ exo read 7893635162b84f78e4475c2d6383645659545344 config --format=raw
    {"a":1,"b":2}
    $ exo info 7893635162b84f78e4475c2d6383645659545344 --include=description --pretty
    {
        "description": {
            "limits": {
                "client": 1,
                "dataport": 10,
                "datarule": 10,
                "disk": "inherit",
                "dispatch": 10,
                "email": 5,
                "email_bucket": "inherit",
                "http": 10,
                "http_bucket": "inherit",
                "share": 5,
                "sms": 0,
                "sms_bucket": 0,
                "xmpp": 10,
                "xmpp_bucket": "inherit"
            },
            "locked": false,
            "meta": "",
            "name": "Temporary CIK",
            "public": false
        }
    }
    '''),
    #('ut', '''Display a tree as fast as possible\n\nUsage:
    #exo [options] ut <cik>'''),
    ('script', '''Upload a Lua script\n\nUsage:
    exo [options] script <cik> [<rid>] --file=<script-file>
    exo [options] script <script-file> <cik> ...

    Both forms do the same thing, but --file is the recommended one.
    If <rid> is omitted, the file name part of <script-file> is used
    as both the alias and name of the script. This convention helps
    when working with scripts in Portals, because Portals shows the
    script resource's name but not its alias.

Command options:
    --name=<name>  script name, if different from script filename. The name
                   is used to identify the script, too.
    --recursive    operate on client and any children
    --create       create the script if it doesn't already exist'''),
    ('spark', '''Show distribution of intervals between points.\n\nUsage:
    exo [options] spark <cik> [<rid>] --days=<days>

Command options:
    --stddev=<num>  exclude intervals more than num standard deviations from mean
    {{ helpoption }}'''),
    ('copy', '''Make a copy of a client.\n\nUsage:
    exo [options] copy <cik> <destination-cik>

    Copies <cik> and all its non-client children to <destination-cik>.
    Returns CIK of the copy. NOTE: copy excludes all data in dataports.

Command options:
    --cikonly  show unlabeled CIK by itself
    {{ helpoption }}'''),
    ('diff', '''Show differences between two clients.\n\nUsage:
    exo [options] diff <cik> <cik2>

    Displays differences between <cik> and <cik2>, including all non-client
    children. If clients are identical, nothing is output. For best results,
    all children should have unique names.

Command options:
    --full         compare all info, even usage, data counts, etc.
    --no-children  don't compare children
    {{ helpoption }}'''),
    ('ip', '''Get IP address of the server.\n\nUsage:
    exo [options] ip'''),
    ('data', '''Read or write with the HTTP Data API.\n\nUsage:
    exo [options] data <cik> [--write=<alias,value> ...] [--read=<alias> ...]

    If only --write arguments are specified, the call is a write.
    If only --read arguments are specified, the call is a read.
    If both --write and --read arguments are specified, the hybrid
        write/read API is used. Writes are executed before reads.'''),
    ('portals', '''Invalidate the Portals cache for a CIK by telling Portals
    a particular procedure was taken on client identified by <cik>.\n\nUsage:
    exo [options] portals clearcache <cik> [<procedure> ...]

    <procedure> may be any of:
    activate, create, deactivate, drop, map, revoke, share, unmap, update

    If no <procedure> is specified, Exoline tells Portals that all of the
    procedures on the list were performed on the client.

    Warning: drop does not invalidate the cache correctly. Instead, use create.
    '''),
    ('share', '''Generate a code that allows non-owners to access resources\n\nUsage:
    exo [options] share <cik> <rid> [--meta=<string> [--share=<code-to-update>]]

    Pass --meta to associate a metadata string with the share.
    Pass --share to update metadata for an existing share.'''),
    ('revoke', '''Revoke a share code\n\nUsage:
    exo [options] revoke <cik> --share=<code>'''),
    ('activate', '''Activate a share code\n\nUsage:
    exo [options] activate <cik> --share=<code>

If you want to activate a *device*, use the "sn activate"
     command instead'''),
    ('deactivate', '''Deactivate a share code\n\nUsage:
    exo [options] deactivate <cik> --share=<code>'''),
    ('clone', '''Create a clone of a client\n\nUsage:
    exo [options] clone <cik> (--rid=<rid> | --share=<code>)

Command options:
     --noaliases     don't copy aliases
     --nohistorical  don't copy time series data
     --noactivate    don't activate CIK of clone (client only)

     The clone command copies the client resource specified by --rid or --share
     into the client specified by <cik>.

     For example, to clone a portals device, pass the portal CIK as <cik> and
     the device RID as <rid>. The portal CIK can be found in Portals
     https://<yourdomain>.exosite.com/account/portals, where it says Key: <cik>.
     A device's RID can be obtained using exo lookup <device-cik>.

     The clone and copy commands do similar things, but clone uses the RPC's
     create (clone) functionality, which is more full featured.
     https://github.com/exosite/docs/tree/master/rpc#create-clone

     Use the clone command except if you need to copy a device to another portal.''')
    ])

# shared sections of documentation
doc_replace = {
    '{{ startend }}': '''<time> can be a unix timestamp or formatted like any of these:

    2011-10-23T08:00:00-07:00
    10/1/2012
    "2012-10-23 14:01 UTC"
    "2012-10-23 14:01"

    If timezone information is omitted, local timezone is assumed
    If time part is omitted, it assumes 00:00:00.
    To report through the present time, omit --end or pass --end=now''',
    '{{ helpoption }}': '''    -h --help  Show this screen.''',
}

plugins = []
if platform.system() != 'Windows':
    # load plugins. use timezone because this file may be running
    # as a script in some other location.
    default_plugin_path = os.path.join(os.path.dirname(timezone.__file__), 'plugins')

    plugin_paths = os.getenv('EXO_PLUGIN_PATH', default_plugin_path).split(':')

    for plugin_path in [i for i in plugin_paths if len(i) > 0]:
        plugin_names = [os.path.basename(f)[:-3]
            for f in glob.glob(plugin_path + "/*.py")
            if not os.path.basename(f).startswith('_')]

        for module_name in plugin_names:
            try:
                plugin = importlib.import_module('plugins.' + module_name)
            except Exception as ex:
		# TODO: only catch the not found exception, for plugin
		# debugging
		#print(ex)
                try:
                    plugin = importlib.import_module('exoline.plugins.' + module_name, package='test')
                except:
                    plugin = importlib.import_module('exoline.plugins.' + module_name)

            # instantiate plugin
            p = plugin.Plugin()
            plugins.append(p)

            # get documentation
            command = p.command()
            if isinstance(command, six.string_types):
                cmd_doc[command] = plugin.__doc__
            else:
                for c in command:
                    cmd_doc[c] = p.doc(c)
else:
    # plugin support for Windows executable build
    try:
        # spec plugin
        try:
            from ..exoline.plugins import spec
        except:
            from exoline.plugins import spec
        p = spec.Plugin()
        plugins.append(p)
        cmd_doc[p.command()] = spec.__doc__

        # transform plugin
        try:
            from ..exoline.plugins import transform
        except:
            from exoline.plugins import transform
        p = transform.Plugin()
        plugins.append(p)
        cmd_doc[p.command()] = transform.__doc__

        # provision plugin
        try:
            from ..exoline.plugins import provision as provisionPlugin
        except:
            from exoline.plugins import provision as provisionPlugin
        p = provisionPlugin.Plugin()
        plugins.append(p)
        for c in p.command():
            cmd_doc[c] = p.doc(c)

        # search plugin
        try:
            from ..exoline.plugins import search
        except:
            from exoline.plugins import search
        p = search.Plugin()
        plugins.append(p)
        cmd_doc[p.command()] = search.__doc__

    except Exception as ex:
        import traceback
        traceback.print_exc()
        pprint(ex)

# perform substitutions on command documentation
for k in cmd_doc:
    # helpoption is appended to any commands that don't already have it
    if '{{ helpoption }}' not in cmd_doc[k]:
        cmd_doc[k] += '\n\nCommand options:\n{{ helpoption }}'
    for r in doc_replace:
        cmd_doc[k] = cmd_doc[k].replace(r, doc_replace[r])

class ExoConfig:
    '''Manages the config file, grouping all realted actions'''
    regex_rid = re.compile("[0-9a-fA-F]{40}")

    def __init__(self, configfile='~/.exoline'):
        configfile = self.realConfigFile(configfile)
        self.loadConfig(configfile)

    def realConfigFile(self, configfile):
        '''Find real path for a config file'''
        # Does the file as passed exist?
        cfgf = os.path.expanduser(configfile)
        if os.path.exists(cfgf):
            return cfgf

        # Is it in the exoline folder?
        cfgf = os.path.join('~/.exoline', configfile)
        cfgf = os.path.expanduser(cfgf)
        if os.path.exists(cfgf):
            return cfgf

        # Or is it a dashed file?
        cfgf = '~/.exoline-' + configfile
        cfgf = os.path.expanduser(cfgf)
        if os.path.exists(cfgf):
            return cfgf

        # No such file to load.
        return None

    def loadConfig(self, configfile):
        if configfile is None:
            self.config = {}
        else:
            try:
                with open(configfile) as f:
                    self.config = yaml.safe_load(f)
            except IOError as ex:
                self.config = {}

    def lookup_shortcut(self, cik):
        '''Look up what was passed for cik in config file
            if it doesn't look like a CIK.'''
        if self.regex_rid.match(cik) is None:
            if 'keys' in self.config:
                if cik in self.config['keys']:
                    return self.config['keys'][cik].strip()
                else:
                    raise ExoException('No CIK shortcut {0}\n{1}'.format(
                        cik, '\n'.join(sorted(self.config['keys']))))
            else:
                raise ExoException('Tried a CIK shortcut {0}, but found no keys'.format(cik))
        else:
            return cik

    def mingleArguments(self, args):
        '''This mixes the settings applied from the configfile and the command line.
        Part of this is making those items availible in both places.
        Command line always overrides configfile.
        '''
        # This ONLY works with options that take a parameter.
        toMingle = ['host', 'port', 'httptimeout', 'useragent', 'portals', 'vendortoken', 'vendor']
        # args overrule config.
        # If not in arg but in config: copy to arg.
        for arg in toMingle:
            if arg in self.config and args['--'+arg] is None:
                args['--'+arg] = self.config[arg]

        # copy args to config.
        for arg in toMingle:
            self.config[arg] = args['--'+arg]


exoconfig = ExoConfig()

class ExolineOnepV1(onep.OnepV1):
    '''Subclass that re-adds deprecated commands needed for devices created
    in Portals before the commands were deprecated.'''

    def _callJsonRPC(self, cik, callrequests, returnreq=False):
        '''Time all calls to _callJsonRPC'''
        try:
            ts = time.time()
            procedures = [cr['procedure'] for cr in callrequests]
            r = onep.OnepV1._callJsonRPC(self, cik, callrequests, returnreq)
        except:
            raise
        finally:
            te = time.time()
            PERF_DATA.append({'cik': cik, 'procedures': procedures, 'seconds': te-ts})
        return r

    def comment(self, cik, rid, visibility, comment, defer=False):
        return self._call('comment', cik, [rid, visibility, comment], defer)


class ExoRPC():
    '''Wrapper for pyonep RPC API.
    Raises exceptions on error and provides some reasonable defaults.'''
    regex_rid = re.compile("[0-9a-fA-F]{40}")
    regex_tweeid = re.compile("rid\.[0-9a-fA-F]{5}")

    class RPCException(Exception):
        pass

    def __init__(self,
                 host=DEFAULT_HOST,
                 port=None,
                 httptimeout=60,
                 https=False,
                 verbose=True,
                 logrequests=False,
                 user_agent=None,
		 curldebug=False):

        if port is None:
            port = DEFAULT_PORT_HTTPS if https else DEFAULT_PORT
        if user_agent is None:
            user_agent = "Exoline {0}".format(__version__)
        self.exo = ExolineOnepV1(
	    host=host,
	    port=port,
	    httptimeout=httptimeout,
	    https=https,
	    agent=user_agent,
	    reuseconnection=True,
	    logrequests=logrequests,
	    curldebug=curldebug)

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
            raise ExoRPC.RPCException(', '.join(['{0}: {1}'.format(msg, t) for msg, t in response]))

    def _raise_for_deferred(self, responses):
        r = []
        for call, isok, response in responses:
            self._raise_for_response(isok, response, call=call)
            r.append(response)
        return r

    def mult(self, cik, commands):
        return self._exomult(cik, commands)

    def _exomult(self, auth, commands):
        '''Takes a list of onep commands with cik omitted, e.g.:
            [['info', {alias: ""}], ['listing']]'''
        if len(commands) == 0:
            return []
        if isinstance(auth, six.string_types):
            cik = auth
        elif type(auth) is dict:
            cik = auth['cik']
            assert(not ('client_id' in auth and 'resource_id' in auth))
            if 'client_id' in auth:
                # print('connecting as ' + json.dumps(auth))
                self.exo.connect_as(auth['client_id'])
            if 'resource_id' in auth:
                # print('connecting as ' + json.dumps(auth))
                self.exo.connect_owner(auth['resource_id'])
        else:
            raise Exception("_exomult: unexpected type for auth " + str(auth))
        assert(not self.exo.has_deferred(cik))
        for c in commands:
            if type(c) is not list:
                raise Exception("_exomult: found invalid command")
            method = getattr(self.exo, c[0])
            method(cik, *c[1:], defer=True)
        assert(self.exo.has_deferred(cik))
        r = self.exo.send_deferred(cik)
        if 'client_id' in auth or 'resource_id' in auth:
            self.exo.connect_as(None)
        responses = self._raise_for_deferred(r)
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
                 chunksize=212):
        '''Generates multiple rids and returns combined timestamped data like this:
               [12314, [1, 77, 'a']
               [12315, [2, 78, None]]
           Where 1, 77, 'a' is the order rids were passed, and None represents
           no data in that dataport for that timestamp.'''
        options = self._readoptions(limit, sort, starttime, endtime, selection)

        def _read(cik, rids, options):
            responses = self._exomult(cik, [['read', rid, options] for rid in rids])
            return self._combinereads(responses, options['sort'])

        if limit <= chunksize :
            for r in _read(cik, rids, options):
                yield r
        else:
            # Read chunks by limit.
            maxLimit = options['limit']
            if 'sort' in options and options['sort'] == 'desc':
                # descending
                if 'endtime' in options:
                    nextStart = options['endtime']
                else:
                    nextStart = ExoUtilities.parse_ts_tuple(datetime.now().timetuple())
                while True:
                    chunkOpt = options.copy()
                    chunkOpt['endtime'] = nextStart
                    chunkOpt['limit'] = chunksize
                    res = _read(cik, rids, chunkOpt);
                    if len(res) == 0:
                        break
                    maxLimit = maxLimit - len(res)
                    if maxLimit <= 0:
                        break;
                    #save oldest
                    nextStart = res[-1][0] - 1
                    for r in res:
                        yield r
            else:
                # ascending
                if 'starttime' in options:
                    nextStart = options['starttime']
                else:
                    nextStart = 0
                while True:
                    chunkOpt = options.copy()
                    chunkOpt['starttime'] = nextStart
                    chunkOpt['limit'] = chunksize
                    res = _read(cik, rids, chunkOpt);
                    if len(res) == 0:
                        break
                    maxLimit = maxLimit - len(res)
                    if maxLimit <= 0:
                        break
                    #save oldest
                    nextStart = res[-1][0] + 1
                    for r in res:
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

    def lookup_owner(self, cik, rid):
        isok, response = self.exo.lookup(cik, 'owner', rid)
        self._raise_for_response(isok, response)
        return response

    def lookup_shared(self, cik, code):
        isok, response = self.exo.lookup(cik, 'shared', code)
        self._raise_for_response(isok, response)
        return response

    def listing(self, cik, types, options={}):
        isok, response = self.exo.listing(cik, types, options)
        self._raise_for_response(isok, response)
        return response

    def _listing_with_info(self, auth, types, info_options={}, listing_options={}, read_options=None):
        '''Return a dict mapping types to dicts mapping RID to info for that
        RID. E.g.:
            {'client': {'<rid0>':<info0>, '<rid1>':<info1>},
             'dataport': {'<rid2>':<info2>, '<rid3>':<info3>}}

             info_options and read_options correspond to the options parameters
                 for info and read.
             read_options if set to something other than None, does a read for
                 any datarule or dataport in the listing, passing read_options
                 as options. The result of the read, a list of timestamp value
                 pairs, is placed inside the info dict in a 'read' property.'''

        assert(len(types) > 0)

        listing = self._exomult(auth, [['listing', types, listing_options]])[0]

        # listing is a dictionary mapping types to lists of RIDs, like this:
        # {'client': ['<rid0>', '<rid1>'], 'dataport': ['<rid2>', '<rid3>']}

        # request info for each rid
        # (rids is a flattened version of listing)
        rids = []
        restype = {}
        for typ in types:
            rids += listing[typ]
            for rid in listing[typ]:
                restype[rid] = typ

        info_commands = [['info', rid, info_options] for rid in rids]
        read_commands = []
        readable_rids = [rid for rid in rids if restype[rid] in ['dataport', 'datarule']]
        if read_options is not None:
            # add reads for readable resource types
            read_commands += [['read', rid, read_options] for rid in readable_rids]
        responses = self._exomult(auth, info_commands + read_commands)
        # From the return values make a dict of dicts
        # use ordered dicts in case someone cares about order in the output
        response_index = 0
        listing_with_info = OrderedDict()
        for typ in types:
            type_response = OrderedDict()
            for rid in listing[typ]:
                type_response[rid] = responses[response_index]
                response_index += 1
                if read_options is not None and rid in readable_rids:
                    type_response[rid]['read'] = responses[len(info_commands) + readable_rids.index(rid)]

            listing_with_info[typ] = type_response

        return listing_with_info

    def info(self,
             cik,
             rid={'alias': ''},
             options={},
             cikonly=False,
             recursive=False,
             level=None):
        '''Returns info for RID as a dict.'''
        if recursive:
            rid = None if type(rid) is dict else rid
            response = self._infotree(cik,
                                      rid=rid,
                                      options=options,
                                      level=level)
        else:
            isok, response = self.exo.info(cik, rid, options)
            self._raise_for_response(isok, response)
        if cikonly:
            if not 'key' in response:
                raise ExoException('{0} has no CIK'.format(rid))
            return response['key']
        else:
            return response

    def flush(self, cik, rids, newerthan=None, olderthan=None):
        args=[]
        options = {}
        if newerthan is not None: options['newerthan'] = newerthan
        if olderthan is not None: options['olderthan'] = olderthan
        if len(options) > 0:
            args.append(options)
        cmds = [['flush', rid] + args for rid in rids]
        self._exomult(cik, cmds)

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

    def share(self, cik, rid, options):
        isok, response = self.exo.share(cik,
                                        rid,
                                        options)
        self._raise_for_response(isok, response)
        return response

    def revoke(self, cik, codetype, code):
        isok, response = self.exo.revoke(cik, codetype, code)
        self._raise_for_response(isok, response)
        return response

    def activate(self, cik, codetype, code):
        isok, response = self.exo.activate(cik, codetype, code)
        self._raise_for_response(isok, response)
        return response

    def deactivate(self, cik, codetype, code):
        isok, response = self.exo.deactivate(cik, codetype, code)
        self._raise_for_response(isok, response)
        return response

    def clone(self, cik, options):
        isok, response = self.exo.create(cik, 'clone', options)
        self._raise_for_response(isok, response)
        return response

    def _print_tree_line(self, line):
        if sys.version_info < (3, 0):
            print(line.encode('utf-8'))
        else:
            print(line)

    def _pretty_date(self, time=False):
        """
        Get a datetime object or a int() Epoch timestamp and return a
        pretty string like 'an hour ago', 'Yesterday', '3 months ago',
        'just now', etc

        http://stackoverflow.com/a/1551394/81346
        """
        from datetime import datetime
        now = datetime.now()
        if type(time) is int:
            diff = now - datetime.fromtimestamp(time)
        elif isinstance(time,datetime):
            diff = now - time
        elif not time:
            diff = now - now
        second_diff = diff.seconds
        day_diff = diff.days

        if day_diff < 0:
            return ''

        if day_diff == 0:
            if second_diff < 10:
                return "just now"
            if second_diff < 60:
                return str(second_diff) + " seconds ago"
            if second_diff < 120:
                return "a minute ago"
            if second_diff < 3600:
                return str(second_diff / 60) + " minutes ago"
            if second_diff < 7200:
                return "an hour ago"
            if second_diff < 86400:
                return str(second_diff / 3600) + " hours ago"
        if day_diff == 1:
            return "Yesterday"
        if day_diff < 7:
            return str(day_diff) + " days ago"
        if day_diff < 31:
            return str(day_diff / 7) + " weeks ago"
        if day_diff < 365:
            return str(day_diff / 30) + " months ago"
        return str(day_diff / 365) + " years ago"

    def _format_timestamp(self, values):
        '''format tree latest point timestamp

        values is up to two most recent values, e.g.:
            [[<timestamp1>, <value1>], [<timestamp0>, <value0>]]'''
        if values is None:
            return None
        if len(values) == 0:
            return ''
        return self._pretty_date(values[0][0])

    def _format_value_with_previous(self, v, prev, maxlen):
        '''Return a string representing the string v, w/maximum length
           maxlen. If v is longer than maxlen, the return value
           should include something that changed from previous
           value prev.'''
        v = repr(v)
        prev = repr(prev)
        if len(v) <= maxlen:
            return v

        sm = difflib.SequenceMatcher(None, prev, v)
        def get_nonmatching_blocks(mb):
            lasti = 0
            out = []
            for m in mb:
                if m.b - lasti > 0:
                    out.append({'i': lasti, 'size': m.b - lasti})
                lasti = m.b + m.size
            return out

        # get the blocks (index, size) of v that changed from prev
        mb = list(sm.get_matching_blocks())
        nonmatching_blocks = get_nonmatching_blocks(mb)

        # get the biggest non-matching block
        #bnb = nmb.sorted(nonmatching_blocks, key=lambda(b): b['size'])[-1]

        def widen_block(block, s, left=0, right=0):
            '''block is a location in s and size in this form:
               {'i': <index>, 'size': <size>}. Return block b
               such that the b is up to widen_by wider on the
               left and right while keeping it within the bounds
               of s. block must be already a subset of s. '''
            out = copy.copy(block)
            for j in range(left):
                # try to add to left
                if out['i'] > 0:
                    out['i'] -= 1
                    out['size'] += 1
            for j in range(right):
                # try to add to right
                if out['i'] + out['size'] < len(s):
                    out['size'] += 1
            return out

        # number of characters of context to show on either side of a difference
        context = 5
        s = ''

        print(prev)
        print(v)
        print(mb)
        print(nonmatching_blocks)

        startblock = widen_block(nonmatching_blocks[0], v, left=context, right=maxlen)
        s = ''
        if startblock['i'] > 0:
            s += '...'
        s += v[startblock['i']:startblock['i']+startblock['size']]
        return s[:maxlen] + ('...' if startblock['i'] + len(s) < maxlen else '')


    def _format_values(self, values, maxlen=20):
        '''format latest value for output with tree

        values is up to two most recent values, e.g.:
            [[<timestamp1>, <value1>], [<timestamp0>, <value0>]]'''
        if values is None:
            return None
        if len(values) == 0:
            return ''

        v = values[0][1]
        if type(v) is float or type(v) is int:
            return str(v)
        elif type(v) is dict:
            return str(v)
        else:
            latest = v.replace('\n', r'\n').replace('\r', r'\r')
            out = (latest[:maxlen - 3] + '...') if len(latest) > maxlen else latest
            return out
            # this is not better
            #prev = values[1][1] if len(values) > 1 else ''
            #v = values[0][1]
            #return self._format_value_with_previous(v, prev, maxlen)

    def _print_node(self, rid, info, aliases, cli_args, spacer, islast, maxlen=None, values=None):
        twee = cli_args['<command>'] == 'twee'
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
            if type(aliases) is list:
                add_opt(True, 'aliases', json.dumps(aliases))
            else:
                add_opt(True, 'aliases', aliases)
        # show RID for clients with no alias, or if --verbose was passed
        ridopt = False
        if typ == 'client':
            if has_alias:
                ridopt = '--verbose'
            else:
                ridopt = True
        add_opt(ridopt, 'rid', rid)
        add_opt('--verbose', 'unit', units)
        val = self._format_values(values, 50 if twee else 20)
        timestamp = self._format_timestamp(values)
        add_opt(values is not None, 'value', None if (val is None or timestamp is None) else val + '/' + timestamp)

        if maxlen == None:
            maxlen = {}
            maxlen['type'] = len(typ)
            maxlen['name'] = len(name)
            maxlen['format'] = 0 if 'format' not in info['description'] else len(info['description']['format'])

        if twee:
            # colors, of course
            class bcolors:
                SPACER = '' if cli_args['--nocolor'] else '\033[0m'
                NAME = '' if cli_args['--nocolor'] else '\033[0m'
                TYPE = '' if cli_args['--nocolor'] else '\033[35m'
                ID = '' if cli_args['--nocolor'] else '\033[32m'
                VALUE = '' if cli_args['--nocolor'] else '\033[33m'
                TIMESTAMP = '' if cli_args['--nocolor'] else '\033[34m'
                PINK = '' if cli_args['--nocolor'] else '\033[35m'
                MODEL = '' if cli_args['--nocolor'] else '\033[36m'
                ENDC = '' if cli_args['--nocolor'] else '\033[0m'

            # the goal here is to make the line short to provide more room for the value
            # so if there's an alias, just use that, since it's
            # if no alias, then the first ten of the RID and the name
            # if multiple alias, then the first alias
            if typ == 'client':
                if cli_args['--rids']:
                    tweeid = bcolors.SPACER + 'rid: ' + bcolors.ID + rid
                else:
                    tweeid = bcolors.SPACER + 'cik: ' + bcolors.ID + id[5:]
            else:
                if cli_args['--rids']:
                    tweeid = bcolors.SPACER + 'rid: ' + bcolors.ID + rid
                else:
                    if aliases is not None and len(aliases) > 0:
                        tweeid = aliases[0]
                    else:
                        tweeid = 'rid.' + rid[:5]

            displayname = ((name + bcolors.SPACER + ' ') if len(name) > 0 else ' ')
            displaytype = {'dataport': 'dp', 'client': 'cl', 'datarule': 'dr', 'dispatch': 'ds'}[typ]
            if 'format' in info['description']:
                displaytype += '.' + {'binary': 'b', 'string': 's', 'float': 'f', 'integer': 'i'}[info['description']['format']]
            else:
                displaytype = '  ' + displaytype


            displaymodel = ''
            if 'sn' in opt and 'model' in opt:
                displaymodel = ' (' + opt['model'] + '#' + opt['sn'] + ')'

            self._print_tree_line(
                bcolors.SPACER +
                spacer +
                bcolors.NAME +
                displayname +
                ' ' * (maxlen['name'] + 1 - len(name)) +
                bcolors.TYPE +
                displaytype + ' ' +
                bcolors.ID +
                tweeid +
                bcolors.SPACER +
                ('' if typ == 'client' else ': ') +
                bcolors.VALUE +
                ('' if val is None else val) +
                bcolors.TIMESTAMP +
                ('' if timestamp is None or len(timestamp) == 0 else ' (' + timestamp + ')') +
                bcolors.MODEL +
                displaymodel +
                bcolors.ENDC)
        else:
            # standard tree
            if 'format' in info['description']:
                fmt = info['description']['format']
                desc = fmt + ' ' * (maxlen['format'] + 1 - len(fmt))
                desc += typ + ' ' * (maxlen['type'] + 1 - len(typ))
                desc += id
            else:
                desc = typ + ' ' * (maxlen['type'] + 1 - len(typ))
                desc += id

            self._print_tree_line('{0}{1}{2} {3} {4}'.format(
                spacer,
                name,
                ' ' * (maxlen['name'] + 1 - len(name)),
                desc,
                '' if len(opt) == 0 else '({0})'.format(', '.join(
                    ['{0}: {1}'.format(k, v) for k, v in iteritems(opt)]))))

    def tree(self, auth, aliases=None, cli_args={}, spacer='', level=0, info_options={}):
        '''Print a tree of entities in OneP'''
        max_level = int(cli_args['--level'])
        # print root node
        isroot = len(spacer) == 0
        if isinstance(auth, six.string_types):
            cik = auth
        elif type(auth) is dict:
            cik = auth['cik']
            rid = auth['client_id']
        else:
            raise ExoException('Unexpected auth type ' + str(type(auth)))
        if isroot:
            # usage and counts are slow, so omit them if we don't need them
            exclude = ['usage', 'counts']
            info_options = self.make_info_options(exclude=exclude)
            rid, info = self._exomult(auth,
                                      [['lookup', 'alias', ''],
                                       ['info', {'alias': ''}, info_options]])
            # info doesn't contain key
            info['key'] = cik
            aliases = info['aliases']
            root_aliases = 'see parent'
            self._print_node(rid,
                             info,
                             root_aliases,
                             cli_args,
                             spacer,
                             True)
            if max_level == 0:
                return
            level += 1

        types = ['dataport', 'datarule', 'dispatch', 'client']
        try:
            # TODO: get shares, too
            should_read = '--values' in cli_args and cli_args['--values']
            listing = self._listing_with_info(auth,
                types=types,
                info_options=info_options,
                listing_options={"owned": True},
                read_options={"limit": 1} if should_read else None)
            # _listing_with_info(): {'client': {'<rid0>':<info0>, '<rid1>':<info1>},
            #                        'dataport': {'<rid2>':<info2>}}
        except pyonep.exceptions.OnePlatformException:
            self._print_tree_line(
                spacer +
                "  └─listing for {0} failed. info['basic']['status'] is \
probably not valid.".format(cik))
        except ExoRPC.RPCException as ex:
            if str(ex).startswith('locked ('):
                self._print_tree_line(
                    spacer +
                    "  └─{0} is locked".format(cik))
            else:
                self._print_tree_line(
                    spacer +
                    "  └─RPC error for {0}: {1}".format(cik, ex))
        else:
            # calculate the maximum length of various things for all children,
            # so we can make things line up in the output.
            maxlen = {}
            namelengths = [len(l[1]['description']['name']) for typ in types for l in iteritems(listing[typ])]
            maxlen['name'] = 0 if len(namelengths) == 0 else max(namelengths)

            typelengths = [len(l[1]['basic']['type']) for typ in types for l in iteritems(listing[typ])]
            maxlen['type'] = 0 if len(typelengths) == 0 else max(typelengths)

            formatlengths = [len(l[1]['description']['format'])
                             for typ in types
                             for l in iteritems(listing[typ])
                             if 'format' in l[1]['description']]
            maxlen['format'] = 0 if len(formatlengths) == 0 else max(formatlengths)

            # print everything
            for t_idx, t in enumerate(types):
                typelisting = OrderedDict(sorted(iteritems(listing[t]), key=lambda x: x[1]['description']['name'].lower()))
                islast_nonempty_type = (t_idx == len(types) - 1) or (all(len(listing[typ]) == 0 for typ in types[t_idx + 1:]))
                for rid_idx, rid in enumerate(typelisting):
                    info = typelisting[rid]
                    islastoftype = rid_idx == len(typelisting) - 1
                    islast = islast_nonempty_type and islastoftype
                    if platform.system() != 'Windows':
                        if islast:
                            child_spacer = spacer + '    '
                            own_spacer   = spacer + '  └─'
                        else:
                            child_spacer = spacer + '  │ '
                            own_spacer   = spacer + '  ├─'
                    else:
                        # Windows executable
                        if islast:
                            child_spacer = spacer + '    '
                            own_spacer   = spacer + '  +-'
                        else:
                            child_spacer = spacer + '  | '
                            own_spacer   = spacer + '  +-'

                    if t == 'client':
                        self._print_node(rid, info, aliases, cli_args, own_spacer, islast, maxlen)
                        if max_level == -1 or level < max_level:
                            self.tree({'cik': cik, 'client_id': rid}, info['aliases'], cli_args, child_spacer, level=level + 1, info_options=info_options)
                    else:
                        self._print_node(rid, info, aliases, cli_args, own_spacer, islast, maxlen, values=info['read'] if 'read' in info else None)

    def drop_all_children(self, cik):
        isok, listing = self.exo.listing(
            cik,
            types=['client', 'dataport', 'datarule', 'dispatch'],
            options={})
        self._raise_for_response(isok, listing)
        rids = itertools.chain(*[listing[t] for t in listing.keys()])
        self._exomult(cik, [['drop', rid] for rid in rids])

    def _lookup_rid_by_name(self, cik, name, types=['datarule']):
        '''Look up RID by name. We use name rather than alias to identify
        scripts created in Portals because it only displays names to the
        user, not aliases. Note that if multiple scripts have the same
        name the first one in the listing is returned.'''
        found_rid = None
        listing = self._listing_with_info(cik, types)
        for typ in listing:
            for rid in listing[typ]:
                if listing[typ][rid]['description']['name'] == name:
                    # return first match
                    return rid
        return None

    def _upload_script(self, cik, name, content, rid=None, meta='', alias=None):
        '''Upload a lua script, either creating one or updating the existing one'''
        desc = {
            'format': 'string',
            'name': name,
            'preprocess': [],
            'rule': {
                'script': content
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
            if alias is None:
                alias = name
            success, rid = self.exo.map(cik, rid, alias)
            if success:
                print("Aliased script to: {0}".format(alias))
            else:
                raise ExoException("Error aliasing script")
        else:
            isok, response = self.exo.update(cik, rid, desc)
            if isok:
                print ("Updated script RID: {0}".format(rid))
            else:
                raise ExoException("Error updating datarule: {0}".format(response))

    def cik_recursive(self, cik, fn):
        '''Run fn on cik and all its client children'''
        fn(cik)
        lwi = self._listing_with_info(cik,
                                      ['client'],
                                      info_options={'key': True})
        # {'client': {'<rid0>':<info0>, '<rid1>':<info1>}]
        for rid in lwi['client']:
            self.cik_recursive(lwi['client'][rid]['key'], fn)

    def upload_script_content(self,
                              ciks,
                              content,
                              name,
                              recursive=False,
                              create=False,
                              filterfn=lambda script: script,
                              rid=None):
        for cik in ciks:
            def up(cik, rid):
                if rid is not None:
                    alias = None
                    if create:
                        # when creating, if <rid> is passed it must be an alias
                        # to use instead of name
                        if type(rid) is not dict:
                            raise ExoException('<rid> must be an alias when passing --create')
                        alias = rid['alias']
                        rid = None
                    self._upload_script(cik, name, content, rid=rid, alias=alias)
                else:
                    rid = self._lookup_rid_by_name(cik, name)
                    if rid is not None or create:
                        self._upload_script(cik, name, content, rid=rid)
                    else:
                        # TODO: move this to spec plugin
                        print("Skipping CIK: {0} -- {1} not found".format(cik, name))
                        if not create:
                            print('Pass --create to create it')

            if recursive:
                self.cik_recursive(cik, lambda cik: up(cik, rid))
            else:
                up(cik, rid)

    def upload_script(self,
                      ciks,
                      filename,
                      name=None,
                      recursive=False,
                      create=False,
                      filterfn=lambda script: script,
                      rid=None):
        try:
            f = open(filename)
        except IOError:
            raise ExoException('Error opening file {0}.'.format(filename))
        else:
            with f:
                content = filterfn(f.read())
                if name is None:
                    # if no name is specified, use the file name as a name
                    name = os.path.basename(filename)
                self.upload_script_content(
                    ciks,
                    content,
                    name=name,
                    recursive=recursive,
                    create=create,
                    filterfn=filterfn,
                    rid=rid)

    def lookup_rid(self, cik, cik_to_find):
        isok, listing = self.exo.listing(cik, types=['client'], options={})
        self._raise_for_response(isok, listing)

        for rid in listing['client']:
            self.exo.info(cik, rid, {'key': True}, defer=True)

        if self.exo.has_deferred(cik):
            responses = self.exo.send_deferred(cik)
            for idx, r in enumerate(responses):
                call, isok, response = r
                self._raise_for_response(isok, response)

                if response['key'] == cik_to_find:
                    return listing['client'][idx]

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
            def check_for_unsupported(rid, info):
                desc = info['description']
                if 'subscribe' in desc and desc['subscribe'] is not None and len(desc['subscribe']) > 0:
                    raise ExoException('''Copy does not yet support resources that use the "subscribe" feature, as RID {0} in the source client does.\nIf you're just copying a device into the same portal consider using the clone command.'''.format(rid));
                return rid
            destcik = exoconfig.lookup_shortcut(destcik)
            infotree = self._infotree(cik, options={}, nodeidfn=check_for_unsupported)

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
        differ = difflib.Differ()

        s1 = json.dumps(dict1, indent=2, sort_keys=True).splitlines(1)
        s2 = json.dumps(dict2, indent=2, sort_keys=True).splitlines(1)

        return list(differ.compare(s1, s2))

    def _infotree(self, cik, rid=None, restype='client', resinfo=None, nodeidfn=lambda rid, info: rid, options={}, level=None, raiseExceptions=True):
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
        try:
            types = ['dataport', 'datarule', 'dispatch', 'client']
            listing = {}
            norid = rid is None
            if norid:
                rid, resinfo = self._exomult(cik, [
                    ['lookup', 'aliased', ''],
                    ['info', {'alias': ''}, options]])
            else:
                if resinfo is None:
                    resinfo = self._exomult(cik, [['info', rid, options]])[0]

            myid = nodeidfn(rid, resinfo)

            if level is not None and level <= 0:
                return {'rid': myid, 'info': resinfo}

            if restype == 'client':
                if not norid:
                    # key is only available to owner (not the resource itself)
                    cik = resinfo['key']
                listing = self._exomult(cik, [['listing', types, {}]])[0]
                rids = [rid for rid in list(itertools.chain.from_iterable([listing[t] for t in types]))]
                infos = self._exomult(cik, [['info', rid, options] for rid in rids])
            else:
                listing = []

            resinfo['children'] = []
            infoIndex = 0
            for typ in types:
                if typ in listing:
                    ridlist = listing[typ]
                    for childrid in ridlist:
                        tr = self._infotree(cik,
                                            rid=childrid,
                                            restype=typ,
                                            resinfo=infos[infoIndex],
                                            nodeidfn=nodeidfn,
                                            options=options,
                                            level=None if level is None else level-1,
                                            raiseExceptions=raiseExceptions)
                        infoIndex += 1
                        resinfo['children'].append(tr)
            resinfo['children'].sort(key=lambda x: x['rid'] if 'rid' in x else '')

            return {'rid': myid, 'info': resinfo}
        except Exception as ex:
            if raiseExceptions:
                raise ex
            else:
                return {'exception': ex, 'cik': cik, 'rid': rid}

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

        cik2 = exoconfig.lookup_shortcut(cik2)

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
                  ['data']]

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
    https://github.com/exosite/docs/tree/master/data'''

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
        r = requests.post(url, headers=headers, data=alias_values)
        self.raise_for_status(r)
        return r.text

    def writeread(self, cik, alias_values, aliases):
        headers = {'X-Exosite-CIK': cik,
                   'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
                   'Accept': 'application/x-www-form-urlencoded; charset=utf-8'}
        url = self.url + '/onep:v1/stack/alias?' + '&'.join(aliases)
        r = requests.post(url, headers=headers, data=alias_values)
        self.raise_for_status(r)
        return r.text

    def ip(self):
        r = requests.get(self.url + '/ip')
        r.raise_for_status()
        return r.text


class ExoPortals():
    '''Provides access to the Portals APIs'''

    # list of procedures that may be included in invalidation data
    writeprocs = ['activate',
                  'create',
                  'deactivate',
                  'drop',
                  'map',
                  'revoke',
                  'share',
                  'unmap',
                  'update']

    def __init__(self, portalsserver='https://portals.exosite.com'):
        self.portalsserver = portalsserver

    def invalidate(self, data):
        # This API is documented here:
        # https://i.exosite.com/display/DEVPORTALS/Portals+Cache+Invalidation+API
        data = json.dumps(data)
        #print('invalidating with ' + data)
        try:
            response = requests.post(self.portalsserver + '/api/portals/v1/cache',
                                     data=data)
        except Exception as ex:
            raise ExoException('Failed to connect to ' + self.portalsserver)
        try:
            response.raise_for_status
        except Exception as ex:
            raise ExoException('Bad status from Portals cache invalidate API call: ' + ex)


class ExoUtilities():

    @classmethod
    def parse_ts(cls, s):
        return None if s is None else ExoUtilities.parse_ts_tuple(parser.parse(s).timetuple())

    @classmethod
    def parse_ts_tuple(cls, t):
        return int(time.mktime(t))

    @classmethod
    def get_startend(cls, args):
        '''Get start and end timestamps based on standard arguments'''
        start = args.get('--start', None)
        end = args.get('--end', None)
        def is_ts(s):
            return s is not None and re.match('^[0-9]+$', s) is not None
        if is_ts(start):
            start = int(start)
        else:
            start = ExoUtilities.parse_ts(start)
        if end == 'now':
            end = None
        elif is_ts(end):
            end = int(end)
        else:
            end = ExoUtilities.parse_ts(end)
        return start, end

    @classmethod
    def format_time(cls, sec):
        '''Formats a time interval for human consumption'''
        intervals = [[60 * 60 * 24, 'd'],
                        [60 * 60, 'h'],
                        [60, 'm']]
        text = ""
        for s, label in intervals:
            if sec >= s and sec // s > 0:
                text = "{0} {1}{2}".format(text, sec // s, label)
                sec -= s * (sec // s)
        if sec > 0:
            text += " {0}s".format(sec)
        return text.strip()


def spark(numbers, empty_val=None):
    """Generate a text based sparkline graph from a list of numbers (ints or
    floats).

    When value is empty_val, show no bar.

    https://github.com/1stvamp/py-sparkblocks

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
            out.append(" ")
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

            if six.PY3:
                unichrfn = chr
            else:
                unichrfn = unichr
            out.append(unichrfn(int(9601 + num)))

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
    intervals = [data[i - 1][0] - data[i][0] for i in range(1, len(data))]
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
        #    sum(map(critfn, intervals)))))
        if six.PY3:
            mapfn = map
        else:
            mapfn = itertools.imap
        bins.append(float(sum(mapfn(critfn, intervals))))

    if False:
        # debug
        print(bins)
        print(num_bins * bin_size)
        print(bin_size)
        print(min_t)
        print(max_t)
        print(set(intervals))

    print(spark(bins, empty_val=0))

    min_label = ExoUtilities.format_time(min_t)
    max_label = ExoUtilities.format_time(max_t)
    sys.stdout.write(min_label)
    sys.stdout.write(' ' * (num_bins - len(min_label) - len(max_label)))
    sys.stdout.write(max_label + '\n')


def read_cmd(er, cik, rids, args):
    '''Read command'''
    if len(rids) == 0:
        # if only a CIK was passed, include all dataports and datarules
        # by default.
        listing = er.listing(cik, ['dataport', 'datarule'], {})
        rids = listing['dataport'] + listing['datarule']
        aliases = er.info(cik, options={'aliases': True})['aliases']
        # look up aliases for column headers
        cmdline_rids = [aliases[rid][0] if rid in aliases else rid for rid in rids]

        # in this case default to showing headers
        headertype = 'rid'
    else:
        cmdline_rids = args['<rid>']
        headertype = args['--header']

    limit = args['--limit']
    limit = 1 if limit is None else int(limit)

    # time range
    start, end = ExoUtilities.get_startend(args)

    timeformat = args['--timeformat']
    if headertype == 'name':
        # look up names of rids
        infos = er._exomult(cik,
                            [['info', r, {'description': True}] for r in rids])
        headers = ['timestamp'] + [i['description']['name'] for i in infos]
    else:
        # use whatever headers were passed at the command line (RIDs or
        # aliases)
        headers = ['timestamp'] + [str(r) for r in cmdline_rids]

    dw = csv.DictWriter(sys.stdout, headers)
    if headertype is not None:
        # write headers
        dw.writerow(dict([(h, h) for h in headers]))

    fmt = args['--format']

    tz = args['--tz']

    if tz == None:
        # default to UTC
        try:
            # this single call is slow if pytz is compressed
            # running pip unzip pytz fixes it
            tz = timezone.localtz()
        except pytz.UnknownTimeZoneError as e:
            # Unable to detect local time zone, defaulting to UTC
            tz = pytz.utc
    else:
        try:
            tz = pytz.timezone(tz)
        except Exception as e:
            #default to utc if error
            raise ExoException('Error parsing --tz option, defaulting to local timezone')

    recarriage = re.compile('\r(?!\\n)')

    def printline(timestamp, val):
        if fmt == 'raw':
            if not six.PY3 and isinstance(val[0], six.string_types):
                # Beer bounty for anyone who can tell me how to make
                # both of these work without this awkward try: except:
                # $ ./testone.sh utf8_test -e py27
                # $ exoline/exo.py read myClient foo --format=raw | tail -100
                try:
                    # this works with stdout piped to
                    print(val[0])
                except UnicodeEncodeError:
                    # this works from inside test using StringIO
                    print(val[0].encode('utf-8'))
            else:
                print(val[0])
        else:
            if timeformat == 'unix':
                dt = timestamp
            elif timeformat == 'iso8601':
                dt = datetime.isoformat(pytz.utc.localize(datetime.utcfromtimestamp(timestamp)))
            elif timeformat == 'excel':
                # This date format works for Excel scatter plots
                dt = pytz.utc.localize(datetime.utcfromtimestamp(timestamp)).strftime('%m/%d/%y %H:%M:%S')
            else:
                dt = pytz.utc.localize(datetime.utcfromtimestamp(timestamp)).astimezone(tz)

            row = {'timestamp': str(dt)}

            def stripcarriage(s):
                # strip carriage returns not followed
                if isinstance(s, six.string_types):
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
                                  selection=args['--selection'],
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
                                  selection=args['--selection'],
                                  starttime=last_t + 1)
            results = list(results)
            results.reverse()

            for t, v in results:
                printline(t, v)

            # flush output for piping this output to other programs
            sys.stdout.flush()

            if len(results) > 0:
                last_t, last_v = results[-1]

            time.sleep(sleep_seconds)
    else:
        chunksize = int(args['--chunksize'])
        result = er.readmult(cik,
                             rids,
                             sort=args['--sort'],
                             starttime=start,
                             endtime=end,
                             limit=limit,
                             selection=args['--selection'],
                             chunksize=chunksize)
        for t, v in result:
            printline(t, v)


def plain_print(arg):
    #raise Exception("{0} {1}".format(arg, type(arg)))
    print(arg)


def pretty_print(arg):
    print(json.dumps(arg, sort_keys=True, indent=4, separators=(',', ': ')))


def handle_args(cmd, args):
    use_https = False if args['--http'] is True else True

    # command-specific http timeout defaults
    if args['--httptimeout'] == '60':
        if args['<command>'] == 'copy':
            args['--httptimeout'] == '480'

    port = args['--port']
    if port is None:
        port = DEFAULT_PORT_HTTPS if use_https else DEFAULT_PORT

    er = ExoRPC(host=args['--host'],
                port=port,
                https=use_https,
                httptimeout=args['--httptimeout'],
                logrequests=args['--clearcache'],
                user_agent=args['--useragent'],
		curldebug=args['--curl'])

    pop = provision.Provision(
	host=args['--host'],
	manage_by_cik=False,
	port=port,
	verbose=True,
	https=use_https,
	raise_api_exceptions=True,
	curldebug=args['--curl'])

    if cmd in ['ip', 'data']:
        if args['--https'] is True or args['--port'] is not None or args['--debughttp'] is True or args['--curl'] is True:
            # TODO: support these
            raise ExoException('--https, --port, --debughttp, and --curl are not supported for ip and data commands.')
        ed = ExoData(url='http://' + args['--host'])

    if cmd in ['portals'] or args['--clearcache']:
        portals = ExoPortals(args['--portals'])

    if '<cik>' in args and args['<cik>'] is not None:
        cik = args['<cik>']
        if type(cik) is list:
            cik = [exoconfig.lookup_shortcut(c) for c in cik]
        else:
            cik = exoconfig.lookup_shortcut(cik)
    else:
        # for data ip command
        cik = None
    def rid_or_alias(rid, cik=None):
        '''Translate what was passed for <rid> to an alias object if
           it doesn't look like a RID.'''
        if er.regex_rid.match(rid) is None:
            if er.regex_tweeid.match(rid) is None:
                return {'alias': rid}
            else:
                # look up full RID based on short version
                tweetype, ridfrag = rid.split('.')
                listing = er.listing(cik, ['client', 'dataport', 'datarule', 'dispatch'], {})
                candidates = []
                for typ in listing:
                    for fullrid in listing[typ]:
                        if fullrid.startswith(ridfrag):
                            candidates.append(fullrid)
                if len(candidates) == 1:
                    return candidates[0]
                elif len(candidates) > 1:
                    raise ExoException('More than one RID starts with ' + ridfrag + '. Better use the full RID.')
                else:
                    raise ExoException('No RID found that starts with ' + ridfrag + '. Is it an immediate child of ' + cik + '?')
        else:
            return rid

    rids = []
    if '<rid>' in args:
        if type(args['<rid>']) is list:
            for rid in args['<rid>']:
                rids.append(rid_or_alias(rid, cik))
        else:
            if args['<rid>'] is None:
                rids.append({"alias": ""})
            else:
                rids.append(rid_or_alias(args['<rid>'], cik))

    if args.get('--pretty', False):
        pr = pretty_print
    else:
        pr = plain_print

    try:
        if cmd == 'read':
            read_cmd(er, cik, rids, args)
        elif cmd == 'write':
            if args['-']:
                val = sys.stdin.read()
                # remove extra newline
                if val[-1] == '\n':
                    val = val[:-1]
                er.write(cik, rids[0], val)
            else:
                er.write(cik, rids[0], args['--value'])
        elif cmd == 'record':
            interval = args['--interval']
            if interval is None:
                # split timestamp, value
                if args['-']:
                    headers = ['timestamp', 'value']
                    if sys.version_info < (3, 0):
                        dr = csv.DictReader(sys.stdin, headers, encoding='utf-8')
                    else:
                        dr = csv.DictReader(sys.stdin, headers)
                    rows = list(dr)
                    chunkcnt=0
                    entries=[]
                    for row in rows:
                        s = row['timestamp']
                        if s is not None and re.match('^[-+]?[0-9]+$', s) is not None:
                            ts = int(s)
                        else:
                            ts = ExoUtilities.parse_ts(s)
                        entries.append([ts, row['value']])
                        chunkcnt += 1
                        if chunkcnt > int(args['--chunksize']):
                            er.record(cik, rids[0], entries)
                            chunkcnt = 0
                            entries=[]
                    if len(entries) > 0:
                        er.record(cik, rids[0], entries)

                else:
                    entries = []
                    has_errors = False
                    tvalues = args['--value']
                    reentry = re.compile('(-?\d+),(.*)')
                    for tv in tvalues:
                        match = reentry.match(tv)
                        if match is None:
                            try:
                                t, v = tv.split(',')
                                if t is not None and re.match('^[-+]?[0-9]+$', t) is not None:
                                    ts = int(t)
                                else:
                                    ts = ExoUtilities.parse_ts(t)
                                entries.append([ts, v])
                            except Exception:
                                sys.stderr.write(
                                    'Line not in <timestamp>,<value> format: {0}'.format(tv))
                                has_errors = True
                        else:
                            g = match.groups()
                            s = g[0]
                            if s is not None and re.match('^[-+]?[0-9]+$', s) is not None:
                                ts = int(s)
                            else:
                                ts = ExoUtilities.parse_ts(s)
                            entries.append([ts, g[1]])

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
            owner_of = args['--owner-of']
            share = args['--share']
            if cik_to_find is not None:
                cik_to_find = exoconfig.lookup_shortcut(cik_to_find)
                rid = er.lookup_rid(cik, cik_to_find)
                if rid is not None:
                    pr(rid)
            elif owner_of is not None:
                rid = er.lookup_owner(cik, owner_of)
                if rid is not None:
                    pr(rid)
            elif share is not None:
                rid = er.lookup_shared(cik, share)
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
            types = args['--types'].split(',')

            options = {}
            tags = args['--tagged']
            if tags is not None:
                options['tagged'] = tags.split(',')
            filters = args['--filters']
            if filters is not None:
                for f in filters.split(','):
                    options[f] = True
            listing = er.listing(cik, types, options)
            if args['--plain']:
                for t in types:
                    for rid in listing[t]:
                        print(rid)
            else:
                pr(json.dumps(listing))
        elif cmd == 'info':
            include = args['--include']
            include = [] if include is None else [key.strip()
                for key in include.split(',')]
            exclude = args['--exclude']
            exclude = [] if exclude is None else [key.strip()
                for key in exclude.split(',')]

            options = er.make_info_options(include, exclude)
            level = args['--level']
            level = None if level is None or args['--recursive'] is False else int(level)
            info = er.info(cik,
                        rids[0],
                        options=options,
                        cikonly=args['--cikonly'],
                        recursive=args['--recursive'],
                        level=level)
            if args['--pretty']:
                pr(info)
            else:
                if args['--cikonly']:
                    pr(info)
                else:
                    # output json
                    pr(json.dumps(info))
        elif cmd == 'flush':
            start, end = ExoUtilities.get_startend(args)
            er.flush(cik, rids, newerthan=start, olderthan=end)
        elif cmd == 'usage':
            allmetrics = ['client',
                        'dataport',
                        'datarule',
                        'dispatch',
                        'email',
                        'http',
                        'sms',
                        'xmpp']

            start, end = ExoUtilities.get_startend(args)
            er.usage(cik, rids[0], allmetrics, start, end)
        # special commands
        elif cmd == 'tree':
            er.tree(cik, cli_args=args)
        elif cmd == 'twee':
            args['--values'] = True
            if platform.system() == 'Windows':
                args['--nocolor'] = True
            er.tree(cik, cli_args=args)
        elif cmd == 'script':
            # cik is a list of ciks
            if args['--file']:
                filename = args['--file']
            else:
                filename = args['<script-file>']
            rid = None if args['<rid>'] is None else rids[0]
            er.upload_script(cik,
                filename,
                name=args['--name'],
                recursive=args['--recursive'],
                create=args['--create'],
                rid=rid)
        elif cmd == 'spark':
            days = int(args['--days'])
            end = ExoUtilities.parse_ts_tuple(datetime.now().timetuple())
            start = ExoUtilities.parse_ts_tuple((datetime.now() - timedelta(days=days)).timetuple())
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
        # TODO: reenable provisioning API activate command
        #elif cmd == 'activate':
        #    pr(ep.activate(args['<vendor>'], args['<model>'], args['<sn>']))
        elif cmd == 'portals':

            procedures = args['<procedure>']
            if len(procedures) == 0:
                procedures = ExoPortals.writeprocs
            else:
                unknownprocs = []
                for p in procedures:
                    if p not in ExoPortals.writeprocs:
                        unknownprocs.append(p)
                if len(unknownprocs) > 0:
                    raise ExoException(
                        'Unknown procedure(s) {0}'.format(','.join(unknownprocs)))
            data = {'auth': {'cik': cik},
                    'calls':[{'procedure': p, 'arguments': [], 'id': i}
                             for i, p in enumerate(procedures)]}
            portals.invalidate(data)
        elif cmd == 'share':
            options = {}
            share = args['--share']
            if share is not None:
                options['share'] = share
            meta = args['--meta']
            if meta is not None:
                options['meta'] = meta
            pr(er.share(cik,
                        rids[0],
                        options))
        elif cmd == 'revoke':
            if args['--share'] is not None:
                typ = 'share'
                code = args['--share']
            else:
                typ = 'client'
                code = args['--client']
            pr(er.revoke(cik, typ, code))
        elif cmd == 'activate':
            if args['--share'] is not None:
                typ = 'share'
                code = args['--share']
            else:
                typ = 'client'
                code = args['--client']
            er.activate(cik, typ, code)
        elif cmd == 'deactivate':
            if args['--share'] is not None:
                typ = 'share'
                code = args['--share']
            else:
                typ = 'client'
                code = args['--client']
            er.deactivate(cik, typ, code)
        elif cmd == 'clone':
            options = {}
            if args['--share'] is not None:
                options['code'] = args['--share']
            if args['--rid'] is not None:
                rid_to_clone = args['--rid']
                if er.regex_rid.match(rid_to_clone) is None:
                    # try to look up RID for an alias
                    alias = rid_to_clone
                    rid_to_clone = er.lookup(cik, alias)
                options['rid'] = rid_to_clone

            options['noaliases'] = args['--noaliases']
            options['nohistorical'] = args['--nohistorical']

            rid = er.clone(cik, options)
            pr('rid: {0}'.format(rid))
            info = er.info(cik, rid, {'basic': True, 'key': True})
            typ = info['basic']['type']
            copycik = info['key']
            if typ == 'client':
                if not args['--noactivate']:
                    er.activate(cik, 'client', copycik)
                # for convenience, look up the cik
                pr('cik: {0}'.format(copycik))

        else:
            # search plugins
            handled = False
            exitcode = 1
            for plugin in plugins:
                if cmd in plugin.command():
                    options = {
                            'cik': cik,
                            'rids': rids,
                            'rpc': er,
                            'provision': pop,
                            'exception': ExoException,
                            'provision-exception': pyonep.exceptions.ProvisionException,
                            'utils': ExoUtilities,
                            'config': exoconfig
                            }
                    try:
                        options['data'] = ed
                    except NameError:
                        # no problem
                        pass
                    exitcode = plugin.run(cmd, args, options)
                    handled = True
                    break
            if not handled:
                raise ExoException("Command not handled")
            return exitcode
    finally:
        if args['--clearcache']:
            for req in er.exo.loggedrequests():
                procs = [c['procedure'] for c in req['calls']]
                # if operation will invalidate the Portals cache...
                if len([p for p in procs if p in ExoPortals.writeprocs]) > 0:
                    portals.invalidate(req)


class DiscreetFilter(object):
    '''Filter stdin/stdout to hide anything that looks like
       an RID'''
    def __init__(self, out):
        self.out = out
        # match the two halves of an RID/CIK
        self.ridre = re.compile('([a-fA-F0-9]{20})([a-fA-F0-9]{20})')

    def write(self, message):
        # hide the second half
        if sys.version_info < (3, 0):
            message = message.decode('utf-8')
        s = self.ridre.sub('\g<1>01234567890123456789', message)
        if sys.version_info < (3, 0):
            s = s.encode('utf-8')
        self.out.write(s)

    def flush(self):
        self.out.flush()

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

    # add the first line of the detailed documentation to
    # the exo --help output. Some lines span newlines.
    max_cmd_length = max(len(cmd) for cmd in cmd_doc)
    command_list = ''
    for cmd in cmd_doc:
        lines = cmd_doc[cmd].split('\n\n')[0].split('\n')
        command_list += '  ' + cmd + ' ' * (max_cmd_length - len(cmd)) + '  ' + lines[0] + '\n'
        for line in lines[1:]:
            command_list += ' ' * max_cmd_length + line + '\n'
    doc = __doc__.replace('{{ command_list }}', command_list)

    try:
        args = docopt(
            doc,
            version="Exosite Command Line {0}".format(__version__),
            options_first=True)
    except SystemExit as ex:
        return ex.code

    global exoconfig
    exoconfig = ExoConfig(args['--config'])

    # get command args
    cmd = args['<command>']
    argv = [cmd] + args['<args>']
    if cmd in cmd_doc:
        # if doc expects yet another command, pass options_first=True
        options_first = True if re.search(
            '^Commands:$',
            cmd_doc[cmd],
            flags=re.MULTILINE) else False
        try:
            args_cmd = docopt(cmd_doc[cmd], argv=argv, options_first=options_first)
        except SystemExit as ex:
            return ex.code
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
    if args['--debughttp'] or args['--curl']:
        logging.getLogger("pyonep.onep").setLevel(logging.DEBUG)
        logging.getLogger("pyonep.provision").setLevel(logging.DEBUG)

    # substitute environment variables
    if args['--host'] is None:
        args['--host'] = os.environ.get('EXO_HOST', DEFAULT_HOST)
    if args['--port'] is None:
        args['--port'] = os.environ.get('EXO_PORT', None)

    exoconfig.mingleArguments(args)

    try:
        exitcode = handle_args(cmd, args)
        if exitcode is None:
            return 0
        else:
            return exitcode
    except ExoException as ex:
        # command line tool threw an exception on purpose
        sys.stderr.write("Command line error: {0}\r\n".format(ex))
        return 1
    except ExoRPC.RPCException as ex:
        # pyonep library call signaled an error in return values
        sys.stderr.write("One Platform error: {0}\r\n".format(ex))
        return 1
    except pyonep.exceptions.ProvisionException as ex:
        # if the body of the provision response is something other
        # than a repeat of the status and reason, show it
        showBody = str(ex).strip() != "HTTP/1.1 {0} {1}".format(
            ex.response.status(),
            ex.response.reason())
        sys.stderr.write(
            "One Platform provisioning exception: {0}{1}\r\n".format(
                ex,
                ' (' + str(ex.response.body).strip() + ')' if showBody else ''))
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


def run(argv, stdin=None):
    '''Runs an exoline command, translating stdin from
    string and stdout to string. Returns a CmdResult.'''
    old = {'stdin': sys.stdin, 'stdout': sys.stdout, 'stderr': sys.stderr}
    try:
        if stdin is None:
            stdin = sys.stdin
        elif isinstance(stdin, six.string_types):
            sio = StringIO()
            if six.PY3:
                sio.write(stdin)
            else:
                sio.write(stdin.encode('utf-8'))
            sio.seek(0)
            stdin = sio
        stdout = StringIO()
        stderr = StringIO()

        exitcode = cmd(argv=argv, stdin=stdin, stdout=stdout, stderr=stderr)
        stdout.seek(0)
        stdout = stdout.read().strip()  # strip to get rid of leading newline
        stderr.seek(0)
        stderr = stderr.read().strip()
    finally:
        # restore stdout, stderr, stdin
        sys.stdin = old['stdin']
        sys.stdout = old['stdout']
        sys.stderr = old['stderr']
    return CmdResult(exitcode, stdout, stderr)


if __name__ == '__main__':
    sys.exit(cmd(sys.argv))

#  vim: set ai et sw=4 ts=4 :
