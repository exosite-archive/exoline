Exoline: Command Line for Exosite
=================================

Exoline is a set of commands for accessing the Exosite [One Platform](http://exosite.com/products/onep) from the command line.

- **exo** - command for the [RPC API](http://developers.exosite.com/display/OP/Remote+Procedure+Call+API)

- **exodata** - command for the [HTTP Data Interface API](http://developers.exosite.com/display/OP/HTTP+Data+Interface+API)


Installation 
------------

To install the latest released version of exoline:

```bash

    $ pip install --upgrade exoline

```

Alternatively, install straight from github:

```bash

    $ pip install -e git://github.com/dweaver/exoline#egg=exoline

```


Environment Variables
---------------------

For convenience, several command line options may be replaced by environment variables.

* EXO\_HOST: host, e.g. m2.exosite.com. This supplies --host to exo and --url for exodata.


Help 
----

For help, run each command with -h from the command line. For example:

```bash

exo --help
Exosite RPC API Command Line Interface
   Provides command line access to the Remote Procedure Call API:
   http://developers.exosite.com/display/OP/Remote+Procedure+Call+API

Usage:
  exo [options] read [--follow] [--limit=<limit>] [--selection=all|autowindow|givenwindow] <cik> <rid>
  exo [options] write <cik> <rid> --value=<value>
  exo [options] record <cik> <rid> ((--value=<timestamp,value> ...) | -)
  exo [options] create <cik> (--type=client|clone|dataport|datarule|dispatch) -
  exo [options] create-dataport <cik> (--format=binary|boolean|float|integer|string) [--name=<name>]
  exo [options] create-client <cik> [--name=<name>]
  exo [options] map <cik> <rid> <alias>
  exo [options] unmap <cik> <alias>
  exo [options] lookup <cik> <alias>
  exo [options] drop <cik> <rid> ...
  exo [options] listing [--plain] <cik> (--type=client|dataport|datarule|dispatch) ...
  exo [options] info <cik> <rid> [--cikonly] 
  exo [options] flush <cik> <rid>
  exo [options] tree <cik> [--verbose]
  exo [options] lookup-rid <cik> <cik-to-find>
  exo [options] drop-all-children <cik>
  exo [options] record-backdate <cik> <rid> --interval=<seconds> ((--value=<value> ...) | -)
  exo [options] upload <cik> <script-file> [--name=<name>]

Options:
  --host=<host>        OneP URL. Default is $EXO_HOST or m2.exosite.com.
  --httptimeout=<sec>  HTTP timeout setting.
  --pretty             Pretty print output
  -h --help            Show this screen.
  -v --version         Show version.

```

```bash

Exosite Data API Command Line Interface
   Provides access to the HTTP Data Interface API:
   http://developers.exosite.com/display/OP/HTTP+Data+Interface+API

Usage:
    exodata read [options] <cik> <alias> ... 
    exodata write [options] <cik> <alias>=<value> ...
    exodata ip [options]

Options:
    -h --help     Show this screen
    -v --version  Show version
    --url=<url>   One Platform URL [default: http://m2.exosite.com]

```

Test
----

To run the tests, type:

```bash

    $ cd test
    $ nosetests --verbose

```

Examples
--------

TODO: Usage examples.


TODO
----

- Add support for update command 
- Document release procedure
- Add command-level help (e.g. exo help tree)
- Support binary datasource format
- Add coverage for tests
