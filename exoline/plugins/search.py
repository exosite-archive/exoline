# -*- coding: utf-8 -*-
'''Search resource names, aliases, and serial numbers for a string

Usage:
    exo [options] search <cik> <query-regex>

Command Options:
    --matchcase  Match case when searching
    --nocolor    Turn off output color (implicit in Windows)

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
            sys.stdout.write("\rSearched {0} resources".format(count[0]))
            sys.stdout.flush()
            return rid

        reflags = re.IGNORECASE if args['--matchcase'] else 0
        def printnodes(node, path, aliases):
            if platform.system() == 'Windows':
                args['--nocolor'] = True
            query = args['<query-regex>']
            include = False

            name = node['info']['description']['name']
            matchColor = '\033[32m'
            resetColor = '\033[0m'
            if (re.search(query, name, flags=reflags)):
                if not args['--nocolor']:
                    name = re.sub('(' + query + ')', matchColor + r'\1' + resetColor, name, flags=reflags)
                include = True
            for i in range(len(aliases if aliases is not None else [])):
                if re.search(query, aliases[i], flags=reflags):
                    if not args['--nocolor']:
                        aliases[i] = re.sub('(' + query + ')', matchColor + r'\1' + resetColor, aliases[i], flags=reflags)
                    include = True

            cik = node['info']['key'] if 'key' in node['info'] else None
            if include:
                p = path[:]
                if cik is None:
                    p = ['cik:' + c[:5] + '...' for c in p[:-1]] + ['cik:' + p[-1]]
                else:
                    p = ['cik:' + c[:5] + '...' for c in p]
                    p.append('cik:' + cik)
                if aliases is None or len(aliases) == 0:
                    if cik is None:
                        p.append('rid:' + node['rid'][:5])
                    a = ''
                else:
                    a = ' aliases:[' + ','.join(['"' + a + '"' for a in aliases]) + ']'
                print("{0}{1} name:{2}".format(
                    ' > '.join(p),
                    a,
                    name))

            children = node['info']['children']
            for child in children:
                rid = child['rid']
                if rid in node['info']['aliases']:
                    aliases = node['info']['aliases'][rid]
                else:
                    aliases = None
                p = path[:]
                p.append(cik)
                printnodes(child, p, aliases)

        info = rpc.info(cik, options={"counts": True})
        # These are pretty slow
        #counts = info['counts']
        #total = counts['client'] + counts['dispatch'] + counts['dataport'] + counts['datarule']
        tree = rpc._infotree(cik, options={"description": True, "key": True, "basic": True, "aliases": True}, nodeidfn=progress, level=None)
        sys.stdout.write('\r')
        sys.stdout.flush()
        tree['info']['key'] = cik
        printnodes(tree, [], None)
