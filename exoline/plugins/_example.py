# -*- coding: utf-8 -*-
'''Print a greeting and the latest value of a dataport.
   This is an example Exoline plugin.

Usage:
    exo [options] hello <cik> <rid>

Command Options:
    --greeting=<greeting>  Custom greeting, in case "hello" is not good
                           enough for you. [default: hello]
    --extra-exclamations   Add three exclamation points to the greeting.
{{ helpoption }}
'''

class Plugin():
    # Return command(s) this plugin supports
    # This should match the Usage information
    # in the docstring at the top of this file.
    def command(self):
        return 'hello'

    # Do a command
    # cmd - the string name of the command
    # args - dictionary of docopt arguments - for custom arguments

    def run(self, cmd, args, options):

        ## Common arguments
        # exo.ExoRPC instance configured with host, port, other options
        rpc = options['rpc']
        # cik is the RPC auth, either a 40 character CIK
        # or auth dictionary, like this {"cik": <cik> ...}
        cik = options['cik']
        # rids is either a 40 character RID or an alias
        # dict, like {"alias": "temperature}. If <rid> is not
        # in the usage docs, then options['rids'] is an empty
        # list.
        rid = options['rids'][0]

        ## Custom arguments, defined in the docstring at the top
        ## of this file. For details of docopt syntax:
        ## https://github.com/docopt/docopt
        greeting = args['--greeting']

        # this is True or False depending on whether it
        # was passed in.
        exclamations = args['--extra-exclamations']

        # if docopt format/arguments get confusing, uncomment this
        print(args)

        # ExoRPC methods will raise an exception if something goes wrong
        points = rpc.read(cik, rid, 1)
        if len(points) == 0:
            print('No value in that dataport')
        else:
            print('{0}, {1}{2}'.format(greeting, points[0][1], '!!!' if exclamations else ''))
