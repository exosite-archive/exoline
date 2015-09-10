# -*- coding: utf-8 -*-
'''Update shortcut keys in .exoline

Usage:
    exo [options] keys
    exo [options] keys add <new_cik> <new_name>

Command Options:
    --hack                 This option hacks the gibson.
    --comment=<comment>    Add comment to key.
{{ helpoption }}
'''

import ruamel.yaml
import os, re

class Plugin():
    regex_rid = re.compile("[0-9a-fA-F]{40}$")

    def command(self):
        return 'keys'

    def run(self, cmd, args, options):
        configfile = self.realConfigFile(os.getenv('EXO_CONFIG', '~/.exoline'))
        try:
            with open(configfile) as f:
                config = ruamel.yaml.load(f, ruamel.yaml.RoundTripLoader)
        except IOError as ex:
            config = {'keys': {}}

        if len(args['<args>']) > 0:
            subcommand = args['<args>'][0]
        else:
            subcommand = None

        if subcommand == "add":
            cik = args["<new_cik>"]
            name = args["<new_name>"]

            if self.regex_rid.match(cik) is None:
                print("{} is not a valid cik".format(cik))
                return

            config['keys'][name] = cik

            if args.get('--comment', False):
                config['keys'].yaml_add_eol_comment(args['--comment'], name)

            print("Added `{}: {}` to {}".format(name, cik, configfile))
        else:
            print(" ".join(map(str, config.get("keys", {}).keys())))
        
        with open(configfile, 'w') as f:
            f.write(ruamel.yaml.dump(config, Dumper=ruamel.yaml.RoundTripDumper))

    def realConfigFile(self, configfile):
        '''Find real path for a config file'''
        # Does the file as passed exist?
        cfgf = os.path.expanduser(configfile)

        if os.path.exists(cfgf):
            return cfgf

        # Is it in the exoline folder?
        cfgf = os.path.join('~/.exoline', configfile)
        cfgf = os.path.expanduser(cfgf)
        if os.path.exists(cfgf):
            return cfgf

        # Or is it a dashed file?
        cfgf = '~/.exoline-' + configfile
        cfgf = os.path.expanduser(cfgf)
        if os.path.exists(cfgf):
            return cfgf

        # No such file to load.
        return None