# -*- coding: utf-8 -*-
'''Move a resource from one parent client to another. 

The <cik> is the parent of both <rid> and <destinationrid>.

            <cik>                                        <cik>
              |                                            |
             / \                                          / \\
            /   \                                        /   \\
           /     \                                      /     \\
      <child1>  <destinationrid>   ...becomes...   <child1>  <destinationrid> 
        /                                                       \\
       /                                                         \\
     <rid>                                                      <rid>

Usage:
    exo [options] move <cik> <rid> <destinationrid>

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
        cik = options['cik']
        rid = options['rids'][0]
        destinationrid = args['<destinationrid>']
        noaliases = args['--no-aliases']
        if noaliases:
            rpc.move(cik, rid, destinationrid, {'aliases': False})
        else:
            rpc.move(cik, rid, destinationrid, {'aliases': True})
