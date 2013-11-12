'''Determine whether a client matches a specification (beta)

Usage:
    exo [options] spec <cik> <spec-yaml> [--ids=<id1,id2,idN>]

Options:
    --update-scripts  Update any scripts that do not match what's on the filesystem
    --create          Create any resources that do not exist
    --ids substitutes values for <% id %> when matching alias.

Specification files are in YAML format (a superset of JSON
with more readable syntax and support for comments) and
look like this:

# Sensor spec
dataports:
    # names are created, but not compared
    - name: Temperature
    # aliases, type, and format are compared
      alias: teststring
      format: float
    - name: LED Control
      alias: led6
      format: integer
    # any dataports not listed but found in the client
    # are ignored. The spec command does not delete things.

scripts:
    # by default, scripts are datarules with
    # names and aliases set to the file name
    - file: files/helloworld.lua
    # you can also set them explicitly
    - file: files/convertCelsius.lua
      name: helloworld2 Name
      # if <% id %> is embedded in aliases
      # or script content, the --ids parameter must
      # be passed in. The spec command then substitutes
      # each ID. In this example, if the command was:
      #
      # $ exo spec mysensor sensorspec.yaml --ids=A,B
      #
      # ...then the spec command looks for *two* script datarules
      # in mysensor would be expected, with aliases
      # convertCelsiusA and convertCelsiusB. Additionally,
      # any instances of <% id %> embedded in convertCelsius.lua
      # file are substituted with A and B before being written
      # to each script datarule.
      #
      alias: convertCelsius<% id %>
'''
import re
import os

import yaml

class Plugin():
    def command(self):
        return 'spec'
    def run(self, cmd, args, options):
        cik = options['cik']
        rpc = options['rpc']
        ExoException = options['exception']
        if cmd == 'spec':
            updatescripts = args['--update-scripts']
            create = args['--create']
            def generate_aliases_and_data(res, args):
                ids = args['--ids']
                if 'alias' in res:
                    alias = res['alias']
                else:
                    if 'file' in res:
                        alias = os.path.basename(res['file'])
                    else:
                        raise ExoException('Resources in spec must have an alias.')

                if reid.search(alias) is None:
                    yield alias, None
                else:
                    alias_template = alias
                    if ids is None:
                        raise ExoException('This spec requires --ids')
                    ids = ids.split(',')
                    for id, alias in [(id, reid.sub(id, alias_template)) for id in ids]:
                        yield alias, {'id': id}

            reid = re.compile('<% *id *%>')

            def infoval(cik, alias):
                return rpc._exomult(
                    cik,
                    [['info', {'alias': alias}, {'description': True, 'basic': True}],
                    ['read', {'alias': alias}, {'limit': 1}]])

            with open(args['<spec-yaml>']) as f:
                spec = yaml.safe_load(f)
                for typ in ['dataport', 'client', 'script']:
                    if typ + 's' in spec:
                        for res in spec[typ + 's']:
                            for alias, resource_data in generate_aliases_and_data(res, args):
                                # TODO: handle nonexistence
                                exists = True
                                try:
                                    info, val = infoval(cik, alias)
                                except rpc.RPCException, e:
                                    exists = False
                                    print('Failed to get info and data from {0}.'.format(alias))
                                    if not create:
                                        print('Pass --create to create it')
                                        continue

                                # TODO: use templating library
                                def template(script):
                                    if resource_data is None:
                                        return script
                                    else:
                                        return reid.sub(resource_data['id'], script)

                                if typ == 'client':
                                    if not exists:
                                        if create:
                                            print('Client creation is not yet supported')
                                        continue
                                elif typ == 'dataport':
                                    format = res['format'] if 'format' in res else 'string'
                                    name = res['name'] if 'name' in res else alias
                                    if not exists and create:
                                        print('Creating dataport with name: {0} alias: {1} format: {2}'.format(
                                            name, alias, format))
                                        rid = rpc.create_dataport(cik, format, name=name)
                                        rpc.map(cik, rid, alias)
                                        info, val = infoval(cik, alias)

                                    if info['basic']['type'] != typ:
                                        raise ExoException('{0} is a {1} but should be a {2}.'.format(alias, info['basic']['type'], typ))

                                    if format != info['description']['format']:
                                        raise ExoException(
                                            '{0} is a {1} but should be a {2}.'.format(
                                            alias, info['description']['format'], format))
                                    #print(alias, resource_data, val)
                                    if 'initial' in res and len(val) == 0:
                                        if create:
                                            value = template(res['initial'])
                                            print('Writing initial value {0}'.format(value))
                                            rpc.write(cik, {'alias': alias}, value)
                                        else:
                                            print('Required initial value not found in {0}. Pass --create to write initial value.'.format(alias))

                                elif typ == 'script':
                                    if 'file' not in res:
                                        raise ExoException('{0} is a script, so it needs a "file" key'.format(alias))
                                    name = res['name'] if 'name' in res else alias


                                    if not exists and create:
                                        rpc.upload_script([cik], res['file'], name=alias, create=True, filterfn=template)
                                        continue

                                    with open(res['file']) as scriptfile:
                                        script_spec = template(scriptfile.read().decode('utf8'))
                                        script_svr = info['description']['rule']['script']
                                        if script_svr != script_spec:
                                            print ('Script for {0} does not match file {1}.'.format(alias, res['file']))
                                            if updatescripts:
                                                print('Uploading script to {0}...'.format(alias))
                                                rpc.upload_script([cik], res['file'], name=name, create=False, filterfn=template)
                                            else:
                                                # show diff
                                                import difflib
                                                differ = difflib.Differ()

                                                differences = '\n'.join(
                                                    difflib.unified_diff(
                                                        script_spec.splitlines(),
                                                        script_svr.splitlines(),
                                                        fromfile=res['file'],
                                                        tofile='info["description"]["rule"]["script"]'))

                                                print(differences)
                                else:
                                    raise ExoException('Found unsupported type {0} in spec.'.format(typ))
