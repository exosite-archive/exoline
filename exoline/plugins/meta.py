# -*- coding: utf-8 -*-
'''Easily get and set the meta on an object in 1P.

This assumes the meta string is valid JSON, unless you pass --raw.

Usage:
    exo [options] meta <cik> [<rid>]
    exo [options] meta <cik> [<rid>] --value=<value>
    exo [options] meta <cik> [<rid>] -

Command Options:
{{ helpoption }}
    --raw               Don't try to parse the meta
    --value=<value>     String to save into meta

'''

from __future__ import unicode_literals
import os
import sys
import json


class Plugin():
    def command(self):
        return 'meta'

    def run(self, cmd, args, options):

        cik = options['cik']
        rid = options['rids'][0]
        rpc = options['rpc']
        ExoException = options['exception']
        ExoUtilities = options['utils']

        info = rpc.info(cik, rid)

        if args['--value'] is not None or args['-']:
            try:
                if args['-']:
                    meta = sys.stdin.read()
                    # remove extra newline
                    if meta[-1] == '\n':
                        meta = meta[:-1]
                else:
                    meta = args['--value']
                if not args['--raw']:
                    js = json.loads(meta)
                    meta = json.dumps(meta,separators=(',', ':'))
                # write meta. update.

                # do I need anything else for just updating meta?
                desc = {'meta': meta}
                rpc.update(cik, rid, desc)
                # XXX Need cik of parent and rid of client to modify meta.

            except Exception as ex:
                raise ExoException("Error updating meta: {0}".format(ex))

        else:
            try:
                rawmeta = info['description']['meta']
                if len(rawmeta) == 0:
                    print()
                elif args['--raw']:
                    print(rawmeta)
                else:
                    meta = json.loads(rawmeta)
                    print(json.dumps(meta,separators=(',', ':')))           
            except Exception as ex:
                raise ExoException("Error parsing JSON in meta: {0}".format(ex))



# vim: set ai et sw=4 ts=4 :
