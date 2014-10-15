# -*- coding: utf-8 -*-
'''Provisioning.

Usage:
    exo [options] provision model list [--shared]
    exo [options] provision model info <model>
    exo [options] provision model create (<rid>|<code>) <model_options>...
    exo [options] provision model delete <model>
    exo [options] provision content list <model>
    exo [options] provision content create <model> <id> [<meta>] [--protected]
    exo [options] provision content delete <model> <id>
    exo [options] provision content info <model> <id>
    exo [options] provision content get <model> <id>
    exo [options] provision content put <model> <id>
    exo [options] provision sn list <model> [--offset=num] [--limit=num]
    exo [options] provision sn ranges <model>
    exo [options] provision sn add <model> <sn> [<extra>]
    exo [options] provision sn addcsv <model> <file>
    exo [options] provision sn addrange <model> <format> <length> <casing> <first> <last>
    exo [options] provision sn del <model> <sn>
    exo [options] provision sn delcsv <model> <file>
    exo [options] provision sn delrange <model> <format> <length> <casing> <first> <last>
    exo [options] provision sn rids <model> <sn>
    exo [options] provision sn groups <model> <sn>
    exo [options] provision sn log <model> <sn>
    exo [options] provision sn create <model> <sn> <ownerRID>
    exo [options] provision sn remap <model> <new_sn> <old_sn>
    exo [options] provision sn regenerateCIK <model> <sn>
    exo [options] provision sn disable <model> <sn>

Command Options:

'''
from __future__ import unicode_literals
import os
import sys
import re
from pyonep import provision


class Plugin():
    def command(self):
        return 'provision'

    def run(self, cmd, args, options):
        cik = options['cik']
        rpc = options['rpc']
        ExoException = options['exception']
        ExoUtilities = options['utils']
		exoconfig = options['config']

        pop = provision.Provision(manage_by_cik=False,
                                port=DEFAULT_PORT_HTTPS,
                                verbose=True,
                                https=True,
                                raise_api_exceptions=True)

#  vim: set ai sw=4 ts=4 :
