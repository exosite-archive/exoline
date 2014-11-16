# -*- coding: utf-8 -*-
'''Provisioning commands'''
from __future__ import unicode_literals
import inspect
import sys
import re
import json
import urllib, mimetypes
import six
if six.PY3:
	import urllib.parse as urlparse
	pathname2url = urllib.request.pathname2url
	unquote = urllib.parse.unquote
else:
	import urlparse
	pathname2url = urllib.pathname2url
	unquote = urllib.unquote

import time

class Plugin():
	def command(self):
		return ['model', 'sn', 'content']

	def doc(self, command):
		if command == 'model':
			return '''Create and manage client models (alpha)

Usage:
    exo [options] model list [--long]
    exo [options] model info <model>
    exo [options] model create <model> (<rid>|<code>) [--noaliases] [--nocomments] [--nohistory]
    exo [options] model delete <model>

Command Options:
    -l --long       Long listing
    --noaliases     Set no aliases option on model create
    --nocomments    Set no comments option on model create
    --nohistory     Set no history option on model create
{{ helpoption }}

See http://github.com/exosite/exoline#provisioning for setup instructions.'''
		elif command == 'content':
			return '''Manage content, e.g. firmware images, for a model (alpha)

Usage:
    exo [options] content list <model> [--long]
    exo [options] content put <model> <id> <file> [--mime=type] [--meta=meta]
    exo [options] content get <model> <id> <file>
    exo [options] content delete <model> <id>
    exo [options] content info <model> <id>

Command Options:
    -l --long       Long listing
    --mime=type     Set the mime type of the uploaded data. Will autodetect if omitted
{{ helpoption }}

See http://github.com/exosite/exoline#provisioning for setup instructions.'''
		elif command == 'sn':
			return '''Manage serial numbers (alpha)

Usage:
    exo [options] sn list <model> [--long] [--offset=num] [--limit=num]
    exo [options] sn add <model> (--file=<file> | <sn>...)
    exo [options] sn delete <model> (--file=<file> | <sn>...)
    exo [options] sn ranges <model>
    exo [options] sn addrange <model> <format> <first> <last> [--length=<digits>] [(--uppercase | --lowercase)]
    exo [options] sn delrange <model> <format> <first> <last> [--length=<digits>] [(--uppercase | --lowercase)]
    exo [options] sn regen <model> <sn>
    exo [options] sn enable <model> <sn> <portal-cik> [--portal-rid=<portal-rid>]
    exo [options] sn disable <model> <sn>
    exo [options] sn activate <model> <sn>

Command Options:
    -l --long       Long listing
    --offset=num    Offset to start listing at [default: 0]
    --limit=num     Maximum entries to return [default: 1000]
{{ helpoption }}

See http://github.com/exosite/exoline#provisioning for setup instructions.'''

	########################
	class model:
		def list(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			key = exoconfig.config['vendortoken']

			mlist = pop.model_list(key)
			if not args['--long']:
				models = mlist.body
				if len(models.strip()) > 0:
					print(models)
			else:
				models = mlist.body.splitlines()
				for model in models:
					mlist = pop.model_info(key, model)
					res = urlparse.parse_qs(mlist.body)
					out = [model]
					if 'code' in res:
						out.append('code.{0}'.format(res['code'][0]))
					elif 'rid' in res:
						out.append('rid.{0}'.format(res['rid'][0]))
					if 'options[]' in res:
						out.extend(res['options[]'])
					print(",".join(out))

		def info(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']
			mlist = pop.model_info(key, args['<model>'])
			print(unquote(mlist.body))

		def create(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			mlist = pop.model_create(key, args['<model>'], args['<rid>'],
				aliases=not args['--noaliases'],
				comments=not args['--nocomments'],
				historical=not args['--nohistory'])
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
				if len(files.strip()) > 0:
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

					res = ",".join([afile, size, updated, protected, mime, meta])
					print(res)


		def info(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']
			mlist = pop.content_info(key, args['<model>'], args['<id>'])
			print(unquote(mlist.body))

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
				if args['<file>'] == '-':
					sys.stdout.write(mlist.body)
				else:
					with open(args['<file>'], 'wb') as f:
						f.write(mlist.body)
			except IOError as ex:
				raise ExoException("Could not write {0}".format(args['<file>']))


		def put(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			ProvisionException = options['provision-exception']
			key = exoconfig.config['vendortoken']

			# if not exist, create.
			try:
				mlist = pop.content_info(key, args['<model>'], args['<id>'])
			except ProvisionException as pe:
				if pe.response.status() == 404:
					meta = args['--meta']
					if meta is None:
						meta = ''
					mlist = pop.content_create(key, args['<model>'], args['<id>'], meta)
				else:
					raise

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
				url = pathname2url(args['<file>'])
				mime, encoding = mimetypes.guess_type(url)
			else:
				mime = args['--mime']

			mlist = pop.content_upload(key, args['<model>'], args['<id>'], data, mime)
			if len(mlist.body.strip()) > 0:
				print(mlist.body)


	########################
	class sn:
		def list(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			ProvisionException = options['provision-exception']
			key = exoconfig.config['vendortoken']

			mlist = pop.serialnumber_list(key, args['<model>'], args['--offset'], args['--limit'])
			lines = mlist.body.splitlines()
			for line in lines:
				sn, rid, extra = line.split(',')
				if not args['--long']:
					print(sn)
				else:
					status=''
					try:
						mlist = pop.serialnumber_info(key, args['<model>'], sn)
						if mlist.status() == 204:
							status = 'unused'
						else:
							status = mlist.body.split(',')[0]
							if status == '':
								status = 'unused'
					except ProvisionException as pe:
						if pe.response.status() == 404:
							status = 'unused'
						elif pe.response.status() == 409:
							status = 'orphaned'
						else:
							status = pe.response.body.split(',')[0]
							if status == '':
								status = 'unused'
					if rid == '':
						rid = '<>'
					print(",".join([sn,status,rid,extra]))

		def info(self, cmd, args, options):
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			mlist = pop.serialnumber_info(key, args['<model>'], args['<sn>'][0])
			print(unquote(mlist.body))

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

			formats = ['base10','base16','mac:48','mac-48','mac.48']
			if args['<format>'] not in formats:
				raise ExoException('Unknown <format> {0}. Options are: {1}'.format(args['<format>'], formats))
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
			'''This hard-to-name command does multiple things:
			 - create a new client by cloning a client model,
			   under the portal RID given
			 - assign a previously added serial number
			 - opens a 24 hour window during which a device
			   can call activate and get a CIK'''

			pop = options['pop']
			exoconfig = options['config']
			rpc = options['rpc']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			# --portalrid is optional, but passing
			# it saves one lookup
			portal_cik = args['<portal-cik>']
			portal_rid = args['--portal-rid']
			if portal_rid is None:
				portal_rid = rpc.lookup(portal_cik, '')
			mlist = pop.serialnumber_enable(key, args['<model>'], args['<sn>'][0], portal_rid)

			# write Portals-like meta fields
			rid = mlist.body
			# raise ExoException('got here. rid of clone is ' + rid + ' portal cik is ' + portal_cik)
			meta = {
				"device": {
					"type": "vendor",
					"model": args['<model>'],
					"vendor": exoconfig.config['vendor'],
					"sn": args['<sn>'][0]
				}
			}
			rpc.update(portal_cik, rid, {'meta': json.dumps(meta)})
			print(rid)

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

			mlist = pop.serialnumber_activate(args['<model>'], args['<sn>'][0], exoconfig.config['vendor'])
			print(mlist.body)


	########################################################################
	def digMethod(self, arglist, robj):
		for name, obj in inspect.getmembers(robj):
			#print('=', name)
			if name == arglist[0]:
				if inspect.isclass(obj):
					return self.digMethod(arglist[1:], obj)
				# ismethod() for python2 compatibility
				# http://stackoverflow.com/a/17019983/81346
				elif inspect.ismethod(obj) or inspect.isfunction(obj):
					return (obj, robj, name)
				break
		return ()

	def run(self, cmd, args, options):
		cik = options['cik']
		rpc = options['rpc']
		provision = options['provision']
		ProvisionException = options['provision-exception']
		ExoException = options['exception']
		ExoUtilities = options['utils']
		exoconfig = options['config']

		err = "This command requires 'vendor' and 'vendortoken' in your Exoline config. See http://github.com/exosite/exoline#provisioning"
		if 'vendortoken' not in exoconfig.config or exoconfig.config['vendortoken'] is None:
			raise ExoException(err)
		if 'vendor' not in exoconfig.config or exoconfig.config['vendor'] is None:
			raise ExoException(err)

		options['pop'] = provision.Provision(manage_by_cik=False,
										port='443',
										verbose=True,
										https=True,
										raise_api_exceptions=True,
									    curldebug=args['--curl'])

		methodInfo = self.digMethod([cmd] + args['<args>'], self)
		if len(methodInfo) == 3:
			meth, obj, name = methodInfo
			if meth is not None and obj is not None:
				meth(obj(), name, args, options)
			else:
				raise ExoException("Could not find requested sub command {0}".format(args['<args>']))
		else:
			raise ExoException("Could not find requested sub command {0}".format(args['<args>']))



#  vim: set ai noet sw=4 ts=4 :
