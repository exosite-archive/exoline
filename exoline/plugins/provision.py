# -*- coding: utf-8 -*-
'''Provisioning.

Usage:
	exo [options] provision model list [--shared]
	exo [options] provision model info <model>
	exo [options] provision model create (<rid>|<code>) [--noaliases] [--nocomments] [--nohistory]
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
	exo [options] provision sn regen <model> <sn>
	exo [options] provision sn disable <model> <sn>

Command Options:
	--shared		something.
	--noaliases		n
	--nocomments	n
	--nohistory		n
	--protected		m
	--offset=num	Offset to start listing at [default: 0]
	--limit=num		Maximum entries to return [default: 1000]


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

	########################
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
			mlist = pop.model_info(key, args['<model>'])
			print(mlist.body)

		def create(self, cmd, args, options):
			pass

		def delete(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']
			if args['<model>'] is None:
				raise ExoException("Missing Model name")
			mlist = pop.model_remove(key, args['<model>'])
			print(mlist.body)

	########################
	class content:
		def list(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			if args['<model>'] is None:
				raise ExoException("Missing Model name")
			mlist = pop.content_list(key, args['<model>'])
			print(mlist.body)

		def info(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']
			if args['<model>'] is None:
				raise ExoException("Missing Model name")
			if args['<id>'] is None:
				raise ExoException("Missing content id")
			mlist = pop.content_info(key, args['<model>'], args['<id>'])
			print(mlist.body)


	########################
	class sn:
		def list(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			if args['<model>'] is None:
				raise ExoException("Missing Model name")
			mlist = pop.serialnumber_list(key, args['<model>'], args['--offset'], args['--limit'])
			print(mlist.body)

		def ranges(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			if args['<model>'] is None:
				raise ExoException("Missing Model name")
			mlist = pop.serialnumber_list(key, args['<model>'], args['--offset'], args['--limit'])
			print(mlist.body)

		def add(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			if args['<model>'] is None:
				raise ExoException("Missing Model name")
			if args['<sn>'] is None:
				raise ExoException("Missing Serial Number")

			mlist = pop.serialnumber_add(key, args['<model>'], args['<sn>'])
			print(mlist.body)

		def addcsv(self, cmd, args, options):
			pass
		def addrange(self, cmd, args, options):
			pass

		def del(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			if args['<model>'] is None:
				raise ExoException("Missing Model name")
			if args['<sn>'] is None:
				raise ExoException("Missing Serial Number")

			mlist = pop.serialnumber_remove(key, args['<model>'], args['<sn>'])
			print(mlist.body)

		def delcsv(self, cmd, args, options):
			pass
		def delrange(self, cmd, args, options):
			pass

		def rids(self, cmd, args, options):
			pass

		def groups(self, cmd, args, options):
			pass

		def log(self, cmd, args, options):
			pass

		def create(self, cmd, args, options):
			pass

		def remap(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			if args['<model>'] is None:
				raise ExoException("Missing Model name")
			if args['<new_sn>'] is None:
				raise ExoException("Missing New Serial Number")
			if args['<old_sn>'] is None:
				raise ExoException("Missing Old Serial Number")

			mlist = pop.serialnumber_remap(key, args['<model>'], args['<new_sn>'], args['<old_sn>'])
			print(mlist.body)


		def regen(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			if args['<model>'] is None:
				raise ExoException("Missing Model name")
			if args['<sn>'] is None:
				raise ExoException("Missing Serial Number")

			mlist = pop.serialnumber_reenable(key, args['<model>'], args['<sn>'])
			print(mlist.body)

		def disable(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			if args['<model>'] is None:
				raise ExoException("Missing Model name")
			if args['<sn>'] is None:
				raise ExoException("Missing Serial Number")

			mlist = pop.serialnumber_disable(key, args['<model>'], args['<sn>'])
			print(mlist.body)



	########################################################################
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
			raise ExoException("Could not find requested sub command {0}".format(args['<args>']))



#  vim: set ai noet sw=4 ts=4 :
