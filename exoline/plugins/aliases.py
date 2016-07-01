# -*- coding: utf-8 -*-
'''Get dataport aliases from a client

Usage:
    exo aliases <auth>
'''


class Plugin():
    def command(self):
        return 'aliases'

    def run(self, cmd, args, options):
        rpc = options['rpc']
        auth = options['auth']
        aliases = rpc.info(auth, options={'aliases': True})['aliases']
        print(" ".join(map(lambda x: str(x[0]), aliases.values())))
