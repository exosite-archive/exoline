# -*- coding: utf-8 -*-
'''Build a list of shortcuts from a client

Usage:
    exo [options] makeShortcuts <cik>

Command Options:
    --level=n   Maximum number of level to dig [default: None]
    --sep=c     Seperator to use between levels [default: :]
    --space=s   What to do with whitespace. camel, snake, remove. [default: camel]

    This plugin will build a list of shortcuts from a CIK and all of its
    children clients.

    This list is suitable to be added to a .exoline file and used as future 
    shortcuts.

'''
from __future__ import unicode_literals
import os
import sys
import re
import json


class Plugin():
    def command(self):
        return 'makeShortcuts'

    def run(self, cmd, args, options):
        cik = options['cik']
        rpc = options['rpc']
        ExoException = options['exception']
        ExoUtilities = options['utils']
        level = args['--level']
        if level == 'None':
            level=None
        else:
            level = int(level)

        def removeWhite(string):
            string = re.sub(r'^\s+','',string)
            string = re.sub(r'\s+$','',string)
            if args['--space'] == 'camel':
                def repl(mo):
                    return mo.group(1).upper()
                return re.sub(r'\s+(.)', repl, string)
            elif args['--space'] == 'snake':
                return re.sub(r'\s+', '_', string)
            else:
                return re.sub(r'\s+', '', string)

        def printnodes(node, path):
            if 'key' in node['info']:
                cik = node['info']['key']
                pp = args['--sep'].join(path)
                pp = removeWhite(pp)
                print("  '{0}': {1}".format(pp, cik))
                try:
                    if len(node['info']['description']['meta']) > 0:
                        meta = json.loads(node['info']['description']['meta'])
                        if 'device' in meta:
                            device = meta['device']
                            if 'model' in device and 'sn' in device:
                                pp = device['model'] + '#' + device['sn']
                                print("  '{0}': {1}".format(pp, cik))
                except:
                    pass

            if 'children' in node['info']:
                children = node['info']['children']
                for child in children:
                    rid = child['rid']
                    # alias?
                    alias = rid[:6]
                    if rid in node['info']['aliases']:
                        alias = node['info']['aliases'][rid][0]
                    elif len(child['info']['description']['name']) > 0:
                        alias = child['info']['description']['name']
                    p = path[:]
                    p.append(alias)
                    printnodes(child, p )

        # This craps out too easily.
        # TODO: Need to switch to using the nodeidfn
        tree = rpc._infotree(cik, level=level)
        tree['info']['key'] = cik
        if rpc.regex_rid.match(args['<cik>']) is None:
            alias = args['<cik>']
        else:
            alias = tree['rid'][:6]
        printnodes(tree, [alias])

#  vim: set ai et sw=4 ts=8 :
