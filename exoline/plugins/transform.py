# -*- coding: utf-8 -*-
'''Transform data on in a dataport by mapping all values (alpha)

Usage:
    exo [options] transform <cik> <rid> <func>

Command Options:
    --cma
    --start=<time>
    --end=<time>             start and end times (see details below)
    {{ helpoption }}

{{ startend }}
'''

from __future__ import unicode_literals
import re
import os
import csv
import sys

class Plugin():
    def command(self):
        return 'transform'

    def run(self, cmd, args, options):

        cik = options['cik']
        rid = options['rids'][0]
        mapFunc = args['<func>']
        mpfn = eval('lambda x: ' + mapFunc)
        rpc = options['rpc']
        ExoException = options['exception']
        ExoUtilities = options['utils']
        cma = args['--cma']

        start, end = ExoUtilities.get_startend(args)

        # read data in range, get as array of values.
        response = rpc.read(cik, rid, 65535, 'asc', start, end, 'all')
        # response is array of arrays

        if len(response) == 0:
            raise ExoException('No data read')

        if cma:
            with open(cik + '-read.csv', 'wb') as cvsfile:
                cw = csv.writer(cvsfile)
                cw.writerows(response)

        # Rotate response so we can pass an array of values to the map
        rotated = zip(*response[::-1])

        # transform
        res = map(mpfn, rotated[1])
        rotated[1] = res

        # Rotate it back so we can 'record' it
        data = zip(*rotated)

        if cma:
            with open(cik + '-transformed.csv', 'wb') as cvsfile:
                cw = csv.writer(cvsfile)
                cw.writerows(data)

        # start, end for read is inclusive.
        # start, end for flush is exclusive.
        # adjust by 1
        if start is not None:
            start = start - 1
        if end is not None:
            end = end + 1 
        rpc.flush(cik, [rid], start, end)

        # Put the modified values back
        rpc.record(cik, rid, data)


# vim: set ai et sw=4 ts=4 :
