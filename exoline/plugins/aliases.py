# -*- coding: utf-8 -*-
'''Get dataport aliases from a CIK

Usage:
    exo aliases <cik>
'''
import re

class Plugin():
    def command(self):
        return 'aliases'

    def run(self, cmd, args, options):
        rpc = options['rpc']
        cik = options['cik']
        aliases = rpc.info(cik, options={'aliases': True})['aliases']
        print(" ".join(map(lambda x: str(x[0]), aliases.values())))