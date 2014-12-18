# -*- coding: utf-8 -*-
'''Search resource names, aliases, serial numbers, and script content

Usage:
    exo [options] search <cik> <query-regex>

Command Options:
    --matchcase   Match case when searching
    --nocolor     Turn off output color (implicit in Windows
                  and Python < 2.7)
    --silent      Don't show search progress
'''
from __future__ import unicode_literals
import os
import sys
import re
import json
import platform

class Plugin():
    def command(self):
        return 'search'

    def run(self, cmd, args, options):
        cik = options['cik']
        rpc = options['rpc']
        ExoException = options['exception']
        ExoUtilities = options['utils']

        count = [0]
        def progress(rid, info):
            count[0] += 1
            sys.stderr.write("\rSearched {0} resources".format(count[0]))
            sys.stderr.flush()
            return rid

        reflags = re.IGNORECASE if args['--matchcase'] else 0
        def searchnodes(node, path, aliases):
            if platform.system() == 'Windows' or sys.version_info < (2, 7):
                args['--nocolor'] = True
            query = args['<query-regex>']
            matches = False

            name = node['info']['description']['name']
            matchColor = '\033[32m'
            resetColor = '\033[0m'

            # search name
            if (re.search(query, name, flags=reflags)):
                if not args['--nocolor']:
                    name = re.sub('(' + query + ')', matchColor + r'\1' + resetColor, name, flags=reflags)
                matches = True

            # search alias
            alias = aliases[0] if len(aliases) > 0 else None
            for i in range(len(aliases)):
                if re.search(query, aliases[i], flags=reflags):
                    alias = aliases[i]
                    if not args['--nocolor']:
                        aliases[i] = re.sub('(' + query + ')', matchColor + r'\1' + resetColor, aliases[i], flags=reflags)
                    matches = True

            # search serial number
            sn = None
            if 'key' in node['info'] and node['info']['key'] is not None:
                try:
                    # search serial number in portals metadata if present
                    # http://developers.exosite.com/display/POR/Developing+for+Portals
                    if len(node['info']['description']['meta']) > 0:
                        meta = json.loads(node['info']['description']['meta'])
                        device = meta['device']
                        if device['type'] == 'vendor':
                            sn = device['model'] + '#' + device['sn']
                            m = re.search(query, sn, flags=reflags)
                            if m is not None:
                                if not args['--nocolor']:
                                    sn = re.sub('(' + query + ')', matchColor + r'\1' + resetColor, sn, flags=reflags)
                            else:
                                sn = None

                except Exception as ex:
                    print(str(ex))
                    pass

            # search script content
            script = None
            description = node['info']['description']
            if 'rule' in description and 'script' in description['rule']:
                if re.search(query, description['rule']['script'], flags=reflags):
                    script = description['rule']['script']
                    if not args['--nocolor']:
                        script = re.sub('(' + query + ')', matchColor + r'\1' + resetColor, script, flags=reflags)
                    matches = True

            cik = node['info']['key'] if 'key' in node['info'] else None
            if matches:
                p = path[:]
                if cik is None:
                    p = ['cik:' + c[:5] + '...' for c in p[:-1]] + ['cik:' + p[-1]]
                else:
                    p = ['cik:' + c[:5] + '...' for c in p]
                    p.append('cik:' + cik)
                if len(aliases) == 0:
                    if cik is None:
                        p.append('rid:' + node['rid'])
                    a = ''
                else:
                    a = ' > alias:' + alias + ' '
                print("{0}{1} name:{2}{3}{4}".format(
                    ' > '.join(p),
                    a,
                    name,
                    ' sn:' + sn if sn is not None else '',
                    '\n' + script if script is not None else ''))

            children = node['info']['children']
            for child in children:
                if 'exception' in child:
                    sys.stderr.write('Skipped a resource due to an exception: {0}\n'.format(str(child)))
                else:
                    rid = child['rid']
                    if rid in node['info']['aliases']:
                        aliases = node['info']['aliases'][rid]
                    else:
                        aliases = []
                    p = path[:]
                    p.append(cik)
                    searchnodes(child, p, aliases)

        # These are pretty slow
        #info = rpc.info(cik, options={"counts": True})
        #counts = info['counts']
        #total = counts['client'] + counts['dispatch'] + counts['dataport'] + counts['datarule']
        tree = rpc._infotree(
            cik,
            options={"description": True, "key": True, "basic": True, "aliases": True},
            nodeidfn=progress if not args['--silent'] else lambda rid, info: rid,
            level=None,
            raiseExceptions=False)
        sys.stderr.write('\r')
        sys.stderr.flush()
        if 'exception' in tree:
            print('Exception was: ' + str(tree))
        else:
            tree['info']['key'] = cik
            searchnodes(tree, [], [])
