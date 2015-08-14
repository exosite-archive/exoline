# -*- coding: utf-8 -*-
'''

Usage:
    exo [options] meta <cik> [<rid>]

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

        if args['--value'] is not None:
            print('tock')
            try:
                meta = args['--value']
                if not args['--raw']:
                    js = json.loads(meta)
                    meta = json.dumps(meta,separators=(',', ':'))
                # write meta. update.

                # do I need anything else for just updating meta?
                desc = {'meta': meta}
                rpc.update(cik, rid, desc)

            except Exception as ex:
                raise ExoException("Error updating meta: {0}".format(ex))

        else:
            try:
                if args['--raw']:
                    print(info['description']['meta'])
                else:
                    meta = json.loads(info['description']['meta'])
                    print(json.dumps(meta,separators=(',', ':')))           
            except Exception as ex:
                raise ExoException("Error parsing JSON in meta: {0}".format(ex))



# vim: set ai et sw=4 ts=4 :
