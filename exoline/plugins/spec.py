# -*- coding: utf-8 -*-
'''Determine whether a client matches a specification (beta)

Usage:
    exo [options] spec <cik> <spec-yaml> [--ids=<id1,id2,idN>]
    exo [options] spec --example

Options:
    --update-scripts  Update any scripts that do not match what's
                      on the filesystem
    --create          Create any resources that do not exist
    --ids substitutes values for <% id %> when matching alias
    --example         Show an annotated example spec YAML file
'''

import re
import os
import json

import yaml

class Plugin():
    def command(self):
        return 'spec'
    def run(self, cmd, args, options):
        if args['--example']:
            print('''
# Example client specification file
# Specification files are in YAML format (a superset of JSON
# with more readable syntax and support for comments) and
# look like this. They may contain comments that begin
# with a # sign.

# list of dataports that must exist
dataports:
      # this the absolute minimum needed to specify a
      # dataport.
    - alias: mystring
      # names are created, but not compared
    - name: Temperature
      # aliases, type, and format are created
      # and compared
      alias: temp
      format: float
      unit: °F
    - name: LED Control
      alias: led6
      format: integer
    - alias: config
      # format should be string, and parseable JSON
      format: string/json
      # initial value (if no other value is read back)
      initial: '{"text": "555-555-1234", "email": "jeff@555.com"}'

    # any dataports not listed but found in the client
    # are ignored. The spec command does not delete things.

# list of script datarules that must exist
scripts:
    # by default, scripts are datarules with
    # names and aliases set to the file name
    - file: files/helloworld.lua
    # you can also set them explicitly
    - file: files/convert.lua
      # if <% id %> is embedded in aliases
      # or script content, the --ids parameter must
      # be passed in. The spec command then expects
      # a script or dataport resource per id passed, substituting
      # each ID for <% id %>. In this example, if the command was:
      #
      # $ exo spec mysensor sensorspec.yaml --ids=A,B
      #
      # ...then the spec command looks for *two* script datarules
      # in mysensor, with aliases convertA.lua and convertB.lua.
      # Additionally, any instances of <% id %> in the content of
      # convert.lua are substituted with A and B before being
      # written to each script datarule.
      #
      alias: convert<% id %>.lua
''')
            return

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
                '''Get info and latest value for a resource'''
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
                                    print('{0} not found.'.format(alias))
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
                                    pieces = format.split('/')
                                    if len(pieces) > 1:
                                        format = pieces[0]
                                        format_content = pieces[1]
                                    else:
                                        format_content = None
                                    name = res['name'] if 'name' in res else alias
                                    if not exists and create:
                                        print('Creating dataport with name: {0}, alias: {1}, format: {2}'.format(
                                            name, alias, format))
                                        rid = rpc.create_dataport(cik, format, name=name)
                                        rpc.map(cik, rid, alias)
                                        info, val = infoval(cik, alias)

                                    # check type
                                    if info['basic']['type'] != typ:
                                        raise ExoException('{0} is a {1} but should be a {2}.'.format(alias, info['basic']['type'], typ))

                                    # check format
                                    if format != info['description']['format']:
                                        raise ExoException(
                                            '{0} is a {1} but should be a {2}.'.format(
                                            alias, info['description']['format'], format))

                                    # check initial value
                                    if 'initial' in res and len(val) == 0:
                                        if create:
                                            initialValue = template(res['initial'])
                                            print('Writing initial value {0}'.format(initialValue))
                                            rpc.write(cik, {'alias': alias}, initialValue)
                                            # update values being validated
                                            info, val = infoval(cik, alias)
                                        else:
                                            print('Required initial value not found in {0}. Pass --create to write initial value.'.format(alias))

                                    # check format content (e.g. json)
                                    if format_content == 'json':
                                        if format != 'string':
                                            raise ExoException(
                                                'Invalid spec for {0}. json content type only applies to string, not {1}.'.format(alias, format));
                                        if len(val) == 0:
                                            print('Spec requires {0} be in JSON format, but it is empty.'.format(alias))
                                        else:
                                            try:
                                                obj = json.loads(val[0][1])
                                            except:
                                                print('Spec requires {0} be in JSON format, but it does not parse as JSON.'.format(alias))
                                    elif format_content is not None:
                                        raise ExoException(
                                            'Invalid spec for {0}. Unrecognized format content {1}'.format(alias, format_content))

                                    # check unit
                                    if 'unit' in res:
                                        meta_string = info['description']['meta']
                                        try:
                                            meta = json.loads(meta_string)
                                        except:
                                            meta = None

                                        def bad_unit_msg(s):
                                            sys.stdout.write('spec expects unit for {0} to be {1}, but they are not.'.format(alias, res['unit']))
                                        def update_meta(meta):
                                            new_desc = info['description'].copy()
                                            new_desc['meta'] = json.dumps(meta)
                                            rpc.update(cik, {'alias': alias}, new_desc)
                                            print(u'unit value for {0} updated to {1}'.format(alias, meta['datasource']['unit']))

                                        if meta is None:
                                            if create:
                                                update_meta({'datasource':{'description':'','unit':res['unit']}})
                                            else:
                                                bad_unit_msg(', but found has no metadata at all. Pass --create to write metadata with unit.')
                                        elif 'datasource' not in meta or 'unit' not in meta['datasource']:
                                            if create:
                                                meta.setdefault('datasource', {})
                                                meta['datasource']['unit'] = res['unit']
                                                update_meta(meta)
                                            else:
                                                bad_unit_msg(', but no unit is specified in metadata. Pass --create to set unit.')
                                        elif meta['datasource']['unit'] != res['unit']:
                                            if create:
                                                meta['datasource']['unit'] = res['unit']
                                                update_meta(meta)
                                            else:
                                                bad_unit_msg(', but metadata specifies unit of {0}. Pass --create to update unit.'.format(meta['datasource']['unit']))

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
