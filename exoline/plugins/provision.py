# -*- coding: utf-8 -*-
'''Provisioning commands'''
from __future__ import unicode_literals
import inspect
import sys
import re
import json
import urllib, mimetypes
import fnmatch
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

from docopt import docopt

INSTRUCTIONS = '''See 'exo {0} <command> --help' for more about a specific command.
See http://github.com/exosite/exoline#provisioning for setup instructions.'''

class Plugin():
	def command(self):
		return ['model', 'sn', 'content']

	def doc(self, command):
		if command == 'model':
			return Plugin.model.doc()
		elif command == 'content':
			return Plugin.content.doc()
		elif command == 'sn':
			return Plugin.sn.doc()

	class Subcommand:
		@classmethod
		def commandlist(cls):
			# add the first line of the detailed documentation to
			# the exo <command> --help output. Some lines span newlines.
			max_cmd_length = max(len(cmd) for cmd in cls.subcommands)
			command_list = ''
			for cmd in cls.subcommands:
				doc = getattr(cls, cmd).__doc__
				lines = doc.split('\n\n')[0].split('\n')
				command_list += '  ' + cmd + ' ' * (max_cmd_length - len(cmd)) + '  ' + lines[0] + '\n'
				for line in lines[1:]:
					command_list += ' ' * (max_cmd_length + 4) + line + '\n'
			return command_list

	########################
	class model(Subcommand):
		subcommands = ['list', 'info']
		@classmethod
		def doc(cls):
			return '''Manage client models for a subdomain (alpha)

Usage:
  exo [options] model [options] <command> [<args> ...]

Commands:
{0}
{1}'''.format(
	cls.commandlist(),
	INSTRUCTIONS.format('model'))

		def list(self, cmd, args, options):
			'''List models for a vendor.

Usage:
    exo [options] model list [<glob>] [--long]

Command options:
    -l --long  Show model RID, noaliases, nocomment, nohistorical
    -h --help  Show this screen'''
			pop = options['pop']
			exoconfig = options['config']
			key = exoconfig.config['vendortoken']

			mlist = pop.model_list(key)
			models = mlist.body.splitlines()
			if args['<glob>'] is not None:
				models = fnmatch.filter(models, args['<glob>'])
			for model in models:
				if not args['--long']:
					print(model.strip())
				else:
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
			'''Get information about a model.

Usage:
    exo [options] model info <model>'''
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']
			mlist = pop.model_info(key, args['<model>'])
			print(unquote(mlist.body))

		def create(self, cmd, args, options):
			'''Create a client model based on a clone template client
WARNING: models created this way are NOT compatible with Portals
without some manual steps.

Usage:
    exo [options] model create <model> (<rid>|<code>) [--noaliases] [--nocomments] [--nohistory]

Command options:
    --noaliases     Set no aliases option on model create
    --nocomments    Set no comments option on model create
    --nohistory     Set no history option on model create

To make a model created with Exoline work in Portals:
1. Go to https://<your subdomain>.exosite.com/admin/managemodels
2. Click the edit button next to this model
3. Enter a Model Name and re-enter the clone template device.

Models created in Portals work just fine in Exoline.
'''

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
			'''Delete a model, including all its content and serial numbers.
WARNING: if you're using Portals, you should use Portals to
delete the model instead of this command.

Usage:
    exo [options] model delete <model>'''
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']
			mlist = pop.model_remove(key, args['<model>'])
			print(mlist.body.strip())

	########################
	class content(Subcommand):
		subcommands = ['list', 'put', 'get', 'delete', 'info']
		@classmethod
		def doc(cls):
			return '''Manage content, e.g. firmware images, for a model (alpha)

Usage:
  exo [options] content [options] <command> [<args> ...]

Commands:
{0}
{1}'''.format(
	cls.commandlist(),
	INSTRUCTIONS.format('content'))

		def list(self, cmd, args, options):
			'''List content entries for a model.

Usage:
    exo [options] content list <model> [<glob>] [--long]

Command options:
    -l --long  Long listing: name, size, updated, protected, mime, meta'''
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
			files = mlist.body.splitlines()
			if args['<glob>'] is not None:
				files = fnmatch.filter(files, args['<glob>'])
			for afile in files:
				if not args['--long']:
					print(afile.strip())
				else:
					mlist = pop.content_info(key, args['<model>'], afile)
					mime, size, updated, meta, protected = mlist.body.strip().split(',')

					# Format into human sizes
					size = humanSize(size)
					# Format into Human time
					#updated = time.strftime('%Y-%m-%dT%H:%M:%S%Z', time.localtime(int(updated)))
					updated = time.strftime('%c', time.localtime(int(updated)))

					res = ",".join([afile, size, updated, protected, mime, meta])
					print(res)

		def info(self, cmd, args, options):
			'''Get information about a content entry.

Usage:
    exo [options] content info <model> <id>'''
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']
			mlist = pop.content_info(key, args['<model>'], args['<id>'])
			print(unquote(mlist.body))

		def delete(self, cmd, args, options):
			'''Delete a content entry.

Usage:
    exo [options] content delete <model> <id>'''
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']
			mlist = pop.content_remove(key, args['<model>'], args['<id>'])
			print(mlist.body)

		def get(self, cmd, args, options):
			'''Get content blob.

Usage:
	exo [options] content get <model> <id> <file>'''

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
						#print('debug', mlist.response.content)
						f.write(mlist.response.content)
			except IOError as ex:
				raise ExoException("Could not write {0}".format(args['<file>']))

		def put(self, cmd, args, options):
			'''Upload content for a model.

Usage:
    exo [options] content put <model> <id> <file> [--mime=type] [--meta=meta] [--protected=<bool>]

Command options:
    --mime=type         Set the mime type of the uploaded data. Will autodetect if omitted
	--protected=<bool>  Set to true to make this content unavailable to other model
						serial numbers [default: false]'''

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
					mlist = pop.content_create(
						key,
						args['<model>'],
						args['<id>'],
						meta,
						protected=args['--protected']=='true')
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
	class sn(Subcommand):
		subcommands = ['list', 'add', 'delete', 'ranges',
				       'addrange', 'delrange', 'regen',
					   'enable', 'disable', 'activate',
					   'log']

		@classmethod
		def doc(cls):
			return '''Manage serial numbers (alpha)

Usage:
  exo [options] sn [options] <command> [<args> ...]

Commands:
{0}
{1}'''.format(
	cls.commandlist(),
	INSTRUCTIONS.format('sn'))

		def list(self, cmd, args, options):
			'''List individual serial numbers added to a model,
not including serial number ranges (see ranges command).

Usage:
    exo [options] sn list <model> [<glob>] [--long] [--offset=num] [--limit=num]

Command options:
    -l --long       Long listing
    --offset=num    Offset to start listing at [default: 0]
    --limit=num     Maximum entries to return [default: 1000]'''

			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			ProvisionException = options['provision-exception']
			key = exoconfig.config['vendortoken']

			mlist = pop.serialnumber_list(key, args['<model>'], args['--offset'], args['--limit'])
			lines = mlist.body.splitlines()
			if args['<glob>'] is not None:
				lines = fnmatch.filter(lines, args['<glob>'])
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
			'''Get information about a serial number.'''
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			mlist = pop.serialnumber_info(key, args['<model>'], args['<sn>'])
			print(unquote(mlist.body))

		def ranges(self, cmd, args, options):
			'''List serial number ranges added to a model.

Usage:
    exo [options] sn ranges <model>'''
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
			'''Add an individual serial number to a model.

Usage:
	exo [options] sn add <model> (--file=<file> | <sn>...)'''
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
			'''Delete an individual serial number from a model.

Usage:
    exo [options] sn delete <model> (--file=<file> | <sn>...)'''
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			if args['--file'] is None:
				mlist = pop.serialnumber_remove_batch(key, args['<model>'], args['<sn>'])
				print(mlist.body.strip())
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
			'''Add a range of serial numbers to the model. This makes
the numbers in the specified range available for enabling devices.

Usage:
    exo [options] sn addrange <model> <format> <first> <last> [(--uppercase | --lowercase)]

Command options:
    --length=<digits>  Require specific number length. Not applicable in mac?48 formats

Details:
    <format> is one of: base10, base16, mac:48, mac-48, mac.48
    <first> is the first number in the range, e.g. 01:01:01:01:00
    <last> is the last number in the range, e.g. 01:01:01:01:ff
    --uppercase and --lowercase specify hex letter case for base16/mac?48
'''
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
			'''Delete a range of serial numbers from the model.

Usage:
    exo [options] sn delrange <model> <format> <first> <last> [--length=<digits>] [(--uppercase | --lowercase)]'''
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
			'''Read a serial number's activation log.

Usage:
    exo [options] sn log <model> <sn>

Output is comma-separated lines in this format:
<timestamp>,<connection-info>,<log-entry>
'''
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			# This should be in the pyonep.provision class. It is not.
			path = '/provision/manage/model/' + args['<model>'] + '/' + args['<sn>'] + '?show=log'
			mlist = pop._request(path, key, '', 'GET', False)
			print(mlist.body.strip())


		def remap(self, cmd, args, options):
			'''TODO: document'''
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			mlist = pop.serialnumber_remap(key, args['<model>'], args['<new_sn>'], args['<old_sn>'])
			print(mlist.body)


		def regen(self, cmd, args, options):
			'''Regenerate CIK for serial number, deactivate the client,
and open a 24 hour window for device to call activate
and get its CIK.

Usage:
    exo [options] sn regen <model> <sn>'''
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			mlist = pop.serialnumber_reenable(key, args['<model>'], args['<sn>'])
			if len(mlist.body.strip()) > 0:
				print(mlist.body.strip())

		def enable(self, cmd, args, options):
			'''Clone a new client from a client model inside
<portal-cik>, assign serial number <sn> to it, and open
a 24 hour window during which a device may call activate
and get a CIK. <portal-cik> must be part of the subdomain
for the model. If successful, output is the RID of the new
client.

Usage:
    exo [options] sn enable <model> <sn> <portal-cik> [--portal-rid=<portal-rid>]

--portal-rid, if supplied, makes the command go a bit
  faster by saving a lookup request for the portal.'''
			pop = options['pop']
			exoconfig = options['config']
			rpc = options['rpc']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			# --portalrid is optional, but passing
			# it saves one lookup
			portal_cik = exoconfig.lookup_shortcut(args['<portal-cik>'])
			portal_rid = args['--portal-rid']
			if portal_rid is None:
				portal_rid = rpc.lookup(portal_cik, '')
			mlist = pop.serialnumber_enable(key, args['<model>'], args['<sn>'], portal_rid)

			# write Portals-like meta fields
			rid = mlist.body
			# raise ExoException('got here. rid of clone is ' + rid + ' portal cik is ' + portal_cik)
			meta = {
				"device": {
					"type": "vendor",
					"model": args['<model>'],
					"vendor": exoconfig.config['vendor'],
					"sn": args['<sn>']
				}
			}
			rpc.update(portal_cik, rid, {'meta': json.dumps(meta)})
			print(rid)

		def disable(self, cmd, args, options):
			'''Disable a client CIK.

Usage:
	exo [options] sn disable <model> <sn>'''
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']
			key = exoconfig.config['vendortoken']

			mlist = pop.serialnumber_disable(key, args['<model>'], args['<sn>'])
			print(mlist.body)

		def activate(self, cmd, args, options):
			'''Activate an enabled serial number and get its CIK.

Usage:
    exo [options] sn activate <model> <sn>

This API is intended to be called from a physical device as it
first comes online at some point during the 24 hour window
initiated by the enable command, but Exoline provides it
for debugging. More about the device-facing activate API is here:

http://docs.exosite.com/provision/device/#provisionactivate'''
			pop = options['pop']
			exoconfig = options['config']
			ExoException = options['exception']

			mlist = pop.serialnumber_activate(args['<model>'], args['<sn>'], exoconfig.config['vendor'])
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

	def findSubcommandClass(self, arglist, robj):
		for name, obj in inspect.getmembers(robj):
			if name == arglist[0]:
				if inspect.isclass(obj):
					return obj
		return None

	def run(self, cmd, args, options):
		cik = options['cik']
		rpc = options['rpc']
		ProvisionException = options['provision-exception']
		ExoException = options['exception']
		ExoUtilities = options['utils']
		exoconfig = options['config']
		options['pop'] = options['provision']

		err = "This command requires 'vendor' and 'vendortoken' in your Exoline config. See http://github.com/exosite/exoline#provisioning"
		if 'vendortoken' not in exoconfig.config or exoconfig.config['vendortoken'] is None:
			raise ExoException(err)
		if 'vendor' not in exoconfig.config or exoconfig.config['vendor'] is None:
			raise ExoException(err)

		argv = [cmd, args['<command>']] + args['<args>']
		methodInfo = self.digMethod(argv, self)
		if len(methodInfo) == 3:
			meth, obj, name = methodInfo
			if meth is not None and obj is not None:
				if args['<command>'] in obj.subcommands:
					doc = meth.__doc__
					try:
						args_cmd = docopt(doc, argv=argv)
					except SystemExit as ex:
						return ExoUtilities.handleSystemExit(ex)
					return meth(obj(), name, args_cmd, options)
				else:
					raise ExoException('Unknown command {0}. Try "exo --help"'.format(args['<command>']))

			else:
				raise ExoException("Could not find requested sub command {0}".format(args['<command>']))
		else:
			# did not find method. Detect help request manually or fail
			if ('-h' in argv or '--help' in argv):
				cls = self.findSubcommandClass(argv, self)
				print(cls.doc())
				return 0
			else:
				raise ExoException("Could not find requested sub command {0}".format(args['<command>']))

#  vim: set ai noet sw=4 ts=4 :
