# -*- coding: utf-8 -*-
'''Build a list of aliases from a client

Usage:
    exo [options] makeAliases <cik>

Command Options:
    --level=n   Maximum number of level to dig [default: None]


    This plugin will build a list of aliases from a CIK and all of its
    children clients.

    This list is suitable to be added to a .exoline file and used as future 
    shortcuts.

'''
from __future__ import unicode_literals
import os
import sys


class Plugin():
    def command(self):
        return 'makeAliases'

    def run(self, cmd, args, options):
        cik = options['cik']
        rpc = options['rpc']
        ExoException = options['exception']
        ExoUtilities = options['utils']
        level = args['--level']

        def printnodes(node, path):
            if 'key' in node['info']:
                cik = node['info']['key']
                pp = ':'.join(path)
                print("  '{0}': {1}".format(pp, cik))
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

        tree = rpc._infotree(cik)
        tree['info']['key'] = cik
        if rpc.regex_rid.match(args['<cik>']) is None:
            alias = args['<cik>']
        else:
            alias = tree['rid'][:6]
        printnodes(tree, [alias])

#  vim: set ai et sw=4 ts=8 :
