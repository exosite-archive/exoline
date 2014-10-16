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
import inspect
import os
import sys
import re
from pyonep import provision


class Plugin():
    def command(self):
        return 'provision'

    class model:
        def list(self, cmd, args, options):
            pop = options['pop']
            exoconfig = options['config']
            key = exoconfig.config['vendortoken']

            mlist = pop.model_list(key)
            models = mlist.body
            print(models)

        def info(self, cmd, args, options):
            pop = options['pop']
            exoconfig = options['config']
            ExoException = options['exception']
            key = exoconfig.config['vendortoken']
            if args['<model>'] is None:
                raise ExoException("Missing Model name")
            else:
                mlist = pop.model_info(key, args['<model>'])
                print(mlist.body)

        def create(self, cmd, args, options):
            pass
        def delete(self, cmd, args, options):
            pass

    class content:
        def list(self, cmd, args, options):
            pop = options['pop']
            exoconfig = options['config']
            ExoException = options['exception']
            key = exoconfig.config['vendortoken']

            if args['<model>'] is None:
                raise ExoException("Missing Model name")
            else:
                mlist = pop.content_list(key, args['<model>'])
                print(mlist.body)

    class sn:
        def list(self, cmd, args, options):
            pop = options['pop']
            exoconfig = options['config']
            ExoException = options['exception']
            key = exoconfig.config['vendortoken']

            if args['<model>'] is None:
                raise ExoException("Missing Model name")
            else:
                mlist = pop.serialnumber_list(key, args['<model>'])
                print(mlist.body)



    def digMethod(self, arglist, robj):
        for name, obj in inspect.getmembers(robj):
            #print('=', name)
            if name == arglist[0]:
                if inspect.isclass(obj):
                    return self.digMethod(arglist[1:], obj)
                elif inspect.ismethod(obj):
                    return (obj, robj, name)
                break
        return ()

    def run(self, cmd, args, options):
        cik = options['cik']
        rpc = options['rpc']
        ExoException = options['exception']
        ExoUtilities = options['utils']
        exoconfig = options['config']

        options['pop'] = provision.Provision(manage_by_cik=False,
                                        port='443',
                                        verbose=True,
                                        https=True,
                                        raise_api_exceptions=True)

        meth, obj, name = self.digMethod(args['<args>'], self)
        if meth is not None and obj is not None:
            meth(obj(), name, args, options)
        else:
            print("not found")



#  vim: set ai et sw=4 ts=4 :
