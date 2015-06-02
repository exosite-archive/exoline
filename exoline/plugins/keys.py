# -*- coding: utf-8 -*-
'''Get keys from ~/.exolinerc

Usage:
    exo keys
'''
import yaml
import os

class Plugin():
    def command(self):
        return 'keys'

    def run(self, cmd, args, options):
        conf = options['config'].config
        print(" ".join(map(str, conf.get("keys", {}).keys())))
        

