# -*- coding: utf-8 -*-
'''Write a zip file with all of a client's data

Usage:
    exo [options] dump <cik> <filename>

Command Options:
    --silent  Don't show search progress

Output file is a zip with this structure:
    dump.json
    infotree.json
    <type1>.<rid1>.json
    <type2>.<rid2>.json
    ...
'''
from __future__ import unicode_literals
import os
import sys
import re
import json
import platform
from datetime import datetime
import zipfile

import six

class Plugin():
    def command(self):
        return 'dump'

    def run(self, cmd, args, options):
        cik = options['cik']
        rpc = options['rpc']
        ExoException = options['exception']
        ExoUtilities = options['utils']

        counts = {
            'resources': 0,
            'points': 0
        }
        def treeprogress(rid, info):
            counts['resources'] += 1
            sys.stderr.write("\rTree: found {0} resources".format(counts['resources']))
            sys.stderr.flush()
            return rid

        MAX_POINTS = 100000000
        current = [0]
        def spinning_cursor():
            while True:
                for cursor in '|/-\\':
                    yield cursor
        spinner = spinning_cursor()
        def seriesprogress(count):
            sys.stderr.write('\b')
            sys.stderr.write(six.next(spinner))
            sys.stderr.flush()
        def dumpTimeSeries(tree, dumpzipfile):
            resources = [c for c in tree['info']['children'] if c['info']['basic']['type'] in ['dataport', 'datarule']]
            for i, resource in enumerate(resources):
                current[0] += 1
                sys.stderr.write("\rReading {0}/{1} time series resources  ".format(current[0], len(resources)))
                sys.stderr.flush()
                data = rpc.readmult(tree['info']['key'], [resource['rid']], MAX_POINTS, sort='asc', starttime=None, endtime=nowts, progress=seriesprogress)
                # pull out just data for this resource
                ts = [[d[0], d[1][0]] for d in data]
                if len(ts) == MAX_POINTS:
                    sys.stderr.write("WARNING: read limit of {0} points for RID {1}\n".format(MAX_POINTS, resource['rid']))
                dumpzipfile.writestr(resource['info']['basic']['type'] + '.' + resource['rid'] + '.json', json.dumps(ts))
                counts['points'] += len(ts)
            sys.stderr.write('\b')
            sys.stderr.flush()

            for c in tree['info']['children']:
                if c['info']['basic']['type'] == 'client':
                    dumpTimeSeries(c, dumpzipfile)

        now = datetime.now()
        nowts = ExoUtilities.parse_ts_tuple(now.timetuple())

        tree = rpc._infotree(
            cik,
            options={"description": True, "key": True, "basic": True, "aliases": True},
            nodeidfn=treeprogress if not args['--silent'] else lambda rid, info: rid,
            level=None,
            raiseExceptions=True)
        sys.stderr.write('\r')
        sys.stderr.flush()

        with zipfile.ZipFile(args['<filename>'], 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            tree['info']['key'] = cik
            try:
                zf.writestr('infotree.json', json.dumps(tree))
                zf.writestr('dump.json', json.dumps({'timestamp': now.isoformat(), 'version': '1.0'}))
                dumpTimeSeries(tree, zf)
            finally:
                zf.close()
                sys.stderr.write('\r')
                sys.stderr.flush()
                print(json.dumps(counts) + '          ')
