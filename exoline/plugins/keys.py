# -*- coding: utf-8 -*-
'''Read and write CIK shortcuts in .exoline config

Usage:
    exo [options] keys
    exo [options] keys add <new_cik> <new_name>
    exo [options] keys rm <name>
    exo [options] keys show <name>
    exo [options] keys clean
    exo [options] keys wipe

Command Options:
    --hack                 This option hacks the gibson.
    --comment=<comment>    Add comment to key.
{{ helpoption }}
'''

import ruamel.yaml as yaml
import os, re
from pyonep.exceptions import OnePlatformException

class Plugin():
    regex_rid = re.compile("[0-9a-fA-F]{40}$")

    def command(self):
        return 'keys'

    def run(self, cmd, args, options):
        rpc = options['rpc']
        config_option = options['config']
        ExoException = options['exception']
        if config_option.configfile is None:
            # normally we don't mention this, but the keys command
            # needs a config file.
            raise ExoException('config file was not found: {0}'.format(
                config_option.askedconfigfile))
        try:
            with open(config_option.configfile) as f:
                config = yaml.load(f, yaml.RoundTripLoader)
                if config['keys'] is None:
                    config['keys'] = {}
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
                print("{0} is not a valid cik".format(cik))
                return

            config['keys'][name] = cik

            if args.get('--comment', False):
                config['keys'].yaml_add_eol_comment(args['--comment'], name)

            print("Added `{0}: {1}` to {2}".format(name, cik, config_option.configfile))
        elif subcommand == "rm":
            name = args["<name>"]

            if config['keys'].get(name, None) == None:
                print("That key does not exist.")
                return

            del config['keys'][name]
        elif subcommand == "show":
            name = args["<name>"]
            print("{0}: {1}".format(name, config['keys'][name]))
        elif subcommand == "wipe":
            del config['keys']
            config['keys'] = {}
        elif subcommand == "clean":
            to_trim = []
            for name in config['keys']:
                try:
                    print("Checking {0}...".format(name)),
                    rpc.info(config['keys'][name], {'alias': ''}, {'basic': True})
                    print("OK")
                except OnePlatformException as e:
                    to_trim.append(name)
                    print("ERR (Removing)")

            if len(to_trim) > 0:
                for name in to_trim:
                    del config['keys'][name]
        else:
            if len(config.get("keys", {})) > 0:
                print(" ".join(map(str, config.get("keys", {}).keys())))

        with open(config_option.configfile, 'w') as f:
            f.write(yaml.dump(config, Dumper=yaml.RoundTripDumper))
