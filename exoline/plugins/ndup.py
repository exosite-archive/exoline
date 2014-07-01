# -*- coding: utf-8 -*-
'''Duplicate a value in a dataport

Usage:
    exo [options] ndup <cik> <rid> [<depth>]

Command Options:
{{ helpoption }}

    This reads the value at <depth> and writes it to dataport.

    It is useful to use a <depth> of 2, in which it becomes a revert of sorts.
    2 is the default for this reason.

'''

from __future__ import unicode_literals
import os
import sys


class Plugin():
    def command(self):
        return 'ndup'

    def run(self, cmd, args, options):

        cik = options['cik']
        rid = options['rids'][0]
        rpc = options['rpc']
        ExoException = options['exception']
        ExoUtilities = options['utils']
        depth = args['<depth>']
        depth = 2 if depth is None else int(depth)

        response = rpc.read(cik, rid, depth, 'desc')
        # response is array of arrays

        if len(response) < depth:
            raise ExoException('No value at that depth')

        value = response[-1]
        rpc.write(cik, rid, value[1])


# vim: set ai et sw=4 ts=4 :
