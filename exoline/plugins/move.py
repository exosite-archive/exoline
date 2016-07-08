# -*- coding: utf-8 -*-
'''Move a resource from one parent client to another.

The <auth> client is the parent of both <rid> and <destinationrid>.

            <auth>                                       <auth>
              |                                            |
             / \                                          / \\
            /   \                                        /   \\
           /     \                                      /     \\
      <child1>  <destinationrid>   ...becomes...   <child1>  <destinationrid>
        /                                                       \\
       /                                                         \\
     <rid>                                                      <rid>

Usage:
    exo [options] move <auth> <rid> <destinationrid>

Command Options:
    --no-aliases  If present then do not move aliases

Command Options:
{{ helpoption }}
'''

class Plugin():
    def command(self):
        return 'move'

    def run(self, cmd, args, options):
        rpc = options['rpc']
        auth = options['auth']
        rid = options['rids'][0]
        destinationrid = args['<destinationrid>']
        noaliases = args['--no-aliases']
        if noaliases:
            rpc.move(auth, rid, destinationrid, {'aliases': False})
        else:
            rpc.move(auth, rid, destinationrid, {'aliases': True})
