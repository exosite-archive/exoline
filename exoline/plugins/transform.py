# -*- coding: utf-8 -*-
'''Transform data on in a dataport by mapping all values (alpha)

Usage:
    exo [options] transform <cik> <rid> <func>

Command Options:
    --cma           Save data to cvs files just in case.
    --dry           Does not flush or record back data.
    --start=<time>
    --end=<time>    start and end times (see details below)
    -v --verbose    display transformed data
{{ helpoption }}

    This plugin allows for applying a transformation function on the data
    values in a dataport.  All values or a subset of them can be modified.

    The intent is that while developing a system, it is not uncommon to
    change what or how the data is stored. A lightweight example is storing
    ADC counts then later deciding to store temperatures. Often this left
    you with the two options of either flushing all the old data and
    waiting for new data to fill. Or trying to deal with the two very
    different data sets.

    <func> is a python snippet to transform the data.  Typically you want
    to stick with simpler things, like converting C into F: 'x*9/5+32'
    or back: '(x-32)*5/9'

    To do more complex things, you can specify a file to use for the
    transform function.  '@<filename>' will import a python module of
    filename. This module needs to have a method at the top level named
    'tr'

    For example, if the following python is in a file 'changefmt.py':
        import json
        def tr(x):
            b = {'data': x}
            return json.dumps(b)

    You could use it with '@changefmt' as <func>


    {{ startend }}
'''

from __future__ import unicode_literals
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
        mpfn = None
        if mapFunc[:1] == '@':
            mapFunc = mapFunc.replace('@','').replace('.py', '')
            trn = __import__(mapFunc)
            mpfn = trn.tr
        else:
            mpfn = eval('lambda x: ' + mapFunc)
        rpc = options['rpc']
        ExoException = options['exception']
        ExoUtilities = options['utils']
        cma = args['--cma']
        dry = args['--dry']
        verbose = args['--verbose']

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

        if verbose:
            cw = csv.writer(sys.stdout)
            cw.writerows(data)

        # start, end for read is inclusive.
        # start, end for flush is exclusive.
        # adjust by 1
        if start is not None:
            start = start - 1
        if end is not None:
            end = end + 1

        if not dry:
            rpc.flush(cik, [rid], start, end)

        # Put the modified values back
        if not dry:
            rpc.record(cik, rid, data)


# vim: set ai et sw=4 ts=4 :
