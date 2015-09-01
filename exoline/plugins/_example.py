# -*- coding: utf-8 -*-
'''Example Exoline plugin. Prints Hello and
   the latest value of a dataport.

Usage:
    exo [options] hello <cik> <rid>

Command Options:
{{ helpoption }}
'''

class Plugin():
    def command(self):
        return 'hello'

    def run(self, cmd, args, options):
        rpc = options['rpc']
        cik = options['cik']
        rid = options['rids'][0]
        points = rpc.read(cik, rid, 1)
        if len(points) == 0:
            print('No value in that dataport')
        else:
            print('Hello, {0}!'.format(points[0][1]))
