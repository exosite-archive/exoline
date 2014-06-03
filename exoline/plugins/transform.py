# -*- coding: utf-8 -*-
'''Transform data on in a dataport by mapping all values (alpha)

Usage:
    exo [options] transform <cik> <rid> <func>

Command Options:
    --start=<time>
    --end=<time>             start and end times (see details below)
    {{ helpoption }}

{{ startend }}
'''

from __future__ import unicode_literals
import re
import os
import json
from pprint import pprint
import sys

def parse_ts(s):
    return None if s is None else parse_ts_tuple(parser.parse(s).timetuple())
def parse_ts_tuple(t):
    return int(time.mktime(t))
def is_ts(s):
    return s is not None and re.match('^[0-9]+$', s) is not None
def get_startend(args):
    '''Get start and end timestamps based on standard arguments'''
    start = args.get('--start', None)
    end = args.get('--end', None)
    if is_ts(start):
        start = int(start)
    else:
        start = parse_ts(start)
    if end == 'now':
        end = None
    elif is_ts(end):
        end = int(end)
    else:
        end = parse_ts(end)
    return start, end

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
        start, end = get_startend(args)

        # read data in range, get as array of values.
        response = rpc.read(cik, rid, 65535, 'asc', start, end, 'all')
        # response is array of arrays

        # Rotate response so we can pass an array of values to the map
        rotated = zip(*response[::-1])

        # transform
        res = map(mpfn, rotated[1])
        rotated[1] = res

        # Rotate it back so we can 'record' it
        data = zip(*rotated)

        print(data)
        #sys.exit()

        # FIXME start and end for read and flush mean different things!
        rpc.flush(cik, [rid], start, end)

        # Put the modified values back
        rpc.record(cik, rid, data)


# vim: set ai noet sw=4 ts=4 :
