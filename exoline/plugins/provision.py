# -*- coding: utf-8 -*-
'''Provisioning. (alpha)
See http://github.com/exosite/exoline#provisioning for vendor token setup instructions.

Usage:
    exo [options] provision model list [--long]
    exo [options] provision model info <model>
    exo [options] provision model create <model> (<rid>|<code>) [--noaliases] [--nocomments] [--nohistory]
    exo [options] provision model delete <model>
    exo [options] provision content list <model> [--long]
    exo [options] provision content put <model> <id> <file> [--mime=type] [--meta=meta]
    exo [options] provision content get <model> <id> <file>
    exo [options] provision content delete <model> <id>
    exo [options] provision content info <model> <id>
    exo [options] provision sn list <model> [--long] [--offset=num] [--limit=num]
    exo [options] provision sn add <model> (--file=<file> | <sn>...)
    exo [options] provision sn delete <model> (--file=<file> | <sn>...)
    exo [options] provision sn ranges <model>
    exo [options] provision sn addrange <model> <format> <first> <last> [--length=<digits>] [(--uppercase | --lowercase)]
    exo [options] provision sn delrange <model> <format> <first> <last> [--length=<digits>] [(--uppercase | --lowercase)]
    exo [options] provision sn regen <model> <sn>
	exo [options] provision sn enable <model> <sn> <rid>
    exo [options] provision sn disable <model> <sn>
    exo [options] provision sn activate <vendor> <model> <sn>

Command Options:
    -l --long       Long listing
    --noaliases     Set no aliases option on model create
    --nocomments    Set no comments option on model create
    --nohistory     Set no history option on model create
    --mime=type     Set the mime type of the uploaded data. Will autodetect if omitted
    --offset=num    Offset to start listing at [default: 0]
    --limit=num     Maximum entries to return [default: 1000]
{{ helpoption }}

'''
from __future__ import unicode_literals
import inspect
import os
import sys
import re
import json
import urllib, mimetypes
import six
if six.PY3:
	import urllib.parse as urlparse
else:
	import urlparse
import time

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
			if not args['--long']:
				models = mlist.body
				print(models)
			else:
				models = mlist.body.splitlines()
				for model in models:
					mlist = pop.model_info(key, model)
					res = urlparse.parse_qs(mlist.body)
					out = [model]
					if 'code' in res:
						out.append(u'code.{0}'.format(res['code'][0]))
					elif 'rid' in res:
						out.append(u'rid.{0}'.format(res['rid'][0]))
					if 'options[]' in res:
						out.extend(res['options[]'])
					print("\t".join(out))

		def info(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']
			mlist = pop.model_info(key, args['<model>'])
			print(mlist.body)

		def create(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			mlist = pop.model_create(key, args['<model>'], args['<rid>'],
					args['--noaliases'] is None,
					args['--nocomments'] is None,
					args['--nohistory'] is None)
			print(mlist.body)


		def delete(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']
			mlist = pop.model_remove(key, args['<model>'])
			print(mlist.body)

	########################
	class content:
		def list(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			ExoUtilities = options['utils']
			key = exoconfig.config['vendortoken']

			def humanSize(size):
				size = int(size)
				if size > (1024*1024):
					return "{0}M".format(size/(1024*1024))
				elif size > 1024:
					return "{0}k".format(size/(1024))
				return "{0}B".format(size)

			mlist = pop.content_list(key, args['<model>'])
			if not args['--long']:
				files = mlist.body
				print(files)
			else:
				files = mlist.body.splitlines()
				for afile in files:
					mlist = pop.content_info(key, args['<model>'], afile)
					mime,size,updated,meta,protected = mlist.body.strip().split(',')

					# Format into human sizes
					size = humanSize(size)
					# Format into Human time
					#updated = time.strftime('%Y-%m-%dT%H:%M:%S%Z', time.localtime(int(updated)))
					updated = time.strftime('%c', time.localtime(int(updated)))

					res = "\t".join([afile, size, updated, protected, mime, meta])
					print(res)


		def info(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']
			mlist = pop.content_info(key, args['<model>'], args['<id>'])
			print(mlist.body)

		def delete(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']
			mlist = pop.content_remove(key, args['<model>'], args['<id>'])
			print(mlist.body)

		def get(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			# This should be in the pyonep.provision class. It is not.
			# This should loop through chunks, not fully pull the file into RAM.
			path = '/provision/manage/content/' + args['<model>'] + '/' + args['<id>'] + '?download=true'
			headers = {"Accept": "*"}
			mlist = pop._request(path, key, '', 'GET', False, headers)

			try:
				if args['<file>'] is '-':
					sys.stdout.write(mlist.body)
				else:
					with open(args['<file>'], 'w') as f:
						f.write(mlist.body)
			except IOError as ex:
				raise ExoException("Could not write {0}".format(args['<file>']))


		def put(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			# if not exist, create.
			mlist = pop.content_info(key, args['<model>'], args['<id>'])
			if mlist.status() == 404:
				meta = args['--meta']
				if meta is None:
					meta = ''
				mlist = pop.content_create(key, args['<model>'], args['<id>'], meta)


			# whats the max size? Are we going to be ok with the pull it
			# all into RAM method? Short term, yes. Long term, No.
			data=''
			try:
				if args['<file>'] == '-':
					data = sys.stdin.read()
				else:
					with open(args['<file>']) as f:
						data = f.read()
			except IOError as ex:
				raise ExoException("Could not read {0}".format(args['<file>']))

			if args['--mime'] is None:
				url = urllib.pathname2url(args['<file>'])
				mime, encoding = mimetypes.guess_type(url)
			else:
				mime = args['--mime']

			mlist = pop.content_upload(key, args['<model>'], args['<id>'], data, mime)
			print(mlist.body)


	########################
	class sn:
		def list(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			mlist = pop.serialnumber_list(key, args['<model>'], args['--offset'], args['--limit'])
			lines = mlist.body.splitlines()
			for line in lines:
				sn, rid, extra = line.split(',')
				if not args['--long']:
					print(sn)
				else:
					if rid == '':
						rid = '<>'
					print("\t".join([sn,rid,extra]))

		def info(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			mlist = pop.serialnumber_info(key, args['<model>'], args['<sn>'][0])
			print(mlist.body)

		def ranges(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			# This should be in the pyonep.provision class. It is not.
			path = '/provision/manage/model/' + args['<model>'] + '/?show=ranges'
			headers = {"Accept": "*"}
			mlist = pop._request(path, key, '', 'GET', False, headers)
			print(mlist.body)


		def add(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			if args['--file'] is None:
				mlist = pop.serialnumber_add_batch(key, args['<model>'], args['<sn>'])
				print(mlist.body)
			else:
				# This should chunk the file from disk to socket.
				data=''
				try:
					if args['--file'] == '-':
						data = sys.stdin.read()
					else:
						with open(args['--file']) as f:
							data = f.read()
				except IOError as ex:
					raise ExoException("Could not read {0}".format(args['--file']))

				# This should be in the pyonep.provision class. It is not.
				path = '/provision/manage/model/' + args['<model>'] + '/'
				headers = {"Content-Type": "text/csv; charset=utf-8"}
				mlist = pop._request(path, key, data, 'POST', False, headers)
				print(mlist.body)

		def delete(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			if args['--file'] is None:
				mlist = pop.serialnumber_remove_batch(key, args['<model>'], args['<sn>'])
				print(mlist.body)
			else:
				# ??? should this raise or trim columns beyond the first???
				# This should chunk the file from disk to socket.
				data=''
				try:
					if args['<file>'] == '-':
						data = sys.stdin.read()
					else:
						with open(args['<file>']) as f:
							data = f.read()
				except IOError as ex:
					raise ExoException("Could not read {0}".format(args['<file>']))

				# This should be in the pyonep.provision class. It is not.
				path = '/provision/manage/model/' + args['<model>'] + '/'
				headers = {"Content-Type": "text/csv; charset=utf-8"}
				mlist = pop._request(path, key, data, 'DELETE', False, headers)
				print(mlist.body)


		def _normalizeRangeEnd(self, string):
			regex_mac = re.compile(r"""^
				(([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}) |
				(([0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}) |
				(([0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4})
				$""", re.VERBOSE)

			number = None

			if re.match(r'^[0-9]+$', string):
				number = int(string)
			elif re.match(r'^(0x)?[0-9A-Fa-f]+$', string):
				number = int(string, 16)
			elif regex_mac.match(string) is not None:
				number = int( re.sub(r'[^0-9A-Fa-f]', '', string), 16)
			else:
				raise ExoException('Range value {0} is not a valid serial number'.format(string))
			return number

		def addrange(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			if args['<format>'] not in ['base10','base16','mac:48','mac-48','mac.48']:
				raise ExoException('Unknown format type {0}'.format(args['<format>']))
			case = 'lower'
			if args['--uppercase'] is not None:
				case = 'upper'
			if args['<format>'] == 'base10':
				case = None

			length = None
			if args['--length'] is not None:
				length = int(args['--length'],0)

			first = self._normalizeRangeEnd(args['<first>'])
			last = self._normalizeRangeEnd(args['<last>'])

			data = {'ranges':[{'format': args['<format>'],
					'length': length,
					'casing': case,
					'first': first,
					'last': last
					}]}

			# This should be in the pyonep.provision class. It is not.
			path = '/provision/manage/model/' + args['<model>'] + '/'
			headers = {"Content-Type": "application/javascript; charset=utf-8"}
			mlist = pop._request(path, key, json.dumps(data), 'POST', False, headers)
			print(mlist.body)

		def delrange(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			if args['<format>'] not in ['base10','base16','mac:48','mac-48','mac.48']:
				raise ExoException('Unknown format type {0}'.format(args['<format>']))
			case = 'lower'
			if args['--uppercase'] is not None:
				case = 'upper'
			if args['<format>'] == 'base10':
				case = None

			length = None
			if args['--length'] is not None:
				length = int(args['--length'],0)

			first = self._normalizeRangeEnd(args['<first>'])
			last = self._normalizeRangeEnd(args['<last>'])

			data = {'ranges':[{'format': args['<format>'],
					'length': length,
					'casing': case,
					'first': first,
					'last': last
					}]}

			# This should be in the pyonep.provision class. It is not.
			path = '/provision/manage/model/' + args['<model>'] + '/'
			headers = {"Content-Type": "application/javascript; charset=utf-8"}
			mlist = pop._request(path, key, json.dumps(data), 'DELETE', False, headers)
			print(mlist.body)


		def log(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			# This should be in the pyonep.provision class. It is not.
			path = '/provision/manage/model/' + args['<model>'] + '/' + args['<sn>'][0] + '?show=log'
			mlist = pop._request(path, key, '', 'GET', False)
			print(mlist.body)


		def remap(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			mlist = pop.serialnumber_remap(key, args['<model>'], args['<new_sn>'], args['<old_sn>'])
			print(mlist.body)


		def regen(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			mlist = pop.serialnumber_reenable(key, args['<model>'], args['<sn>'][0])
			print(mlist.body)

		def enable(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			mlist = pop.serialnumber_enable(key, args['<model>'], args['<sn>'][0], args['<rid>'])
			print(mlist.body)


		def disable(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			mlist = pop.serialnumber_disable(key, args['<model>'], args['<sn>'][0])
			print(mlist.body)

		def activate(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']

			mlist = pop.serialnumber_activate(args['<model>'], args['<sn>'][0], args['<vendor>'])
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
		provision = options['provision']
		ExoException = options['exception']
		ExoUtilities = options['utils']
		exoconfig = options['config']

		if 'vendortoken' not in exoconfig.config:
			raise ExoException("This command requires a vendor token in your Exoline config. See http://github.com/exosite/exoline#provisioning for instructions.")

		options['pop'] = provision.Provision(manage_by_cik=False,
										port='443',
										verbose=True,
										https=True,
										raise_api_exceptions=False)

		meth, obj, name = self.digMethod(args['<args>'], self)
		if meth is not None and obj is not None:
			meth(obj(), name, args, options)
		else:
			raise ExoException("Could not find requested sub command {0}".format(args['<args>']))



#  vim: set ai noet sw=4 ts=4 :
