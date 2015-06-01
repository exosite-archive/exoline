# -*- coding: utf-8 -*-
'''Get switches for a command from its documentation

Usage:
    exo switches <cmd>
'''
import sys
import re

class Plugin():
    def command(self):
        return 'switches'

    def run(self, cmd, args, options):
		doc=options['doc'].get(args["<args>"][-1], "")
		print(" ".join(set(r for r in re.findall(r"(--\w+[^= \n()<>])", doc) if r.startswith("-"))))
