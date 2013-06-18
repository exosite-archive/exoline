# Exoline - Exosite Command Line

Exoline provides several commands for talking to Exosite's [One Platform](http://exosite.com/products/onep)

* __exo__ - command to talk to the [RPC API](http://developers.exosite.com/display/OP/Remote+Procedure+Call+API)

* __exodata__ - command to talk to the [HTTP Data Interface API](http://developers.exosite.com/display/OP/HTTP+Data+Interface+API)


## Setup 

1. Install [pip](https://pypi.python.org/pypi/pip). E.g., for Debian:

    $ sudo apt-get install python-pip 

2. Install [virtualenv](https://pypi.python.org/pypi/virtualenv).

    $ sudo pip install virtualenv 

3. Create virtual environment for this project. E.g.:

    $ virtualenv ve

4. Activate virtual environment. E.g.:
 
    $ source ve/bin/activate
    
5. Install required python modules:

    $ pip install -r requirements.txt
    

## Environment Variables

For convenience, several command line options may be replaced by environment variables.

* EXO\_HOST: host, e.g. m2.exosite.com. This supplies --host to exo and --url for exodata.


## Help 

For help, run each command with -h from the command line. For example:

```
    $ ./exo -h

Exosite RPC API Command Line Interface
   Provides command line access to the Remote Procedure Call API:
   http://developers.exosite.com/display/OP/Remote+Procedure+Call+API

Usage:
  exo [options] create-dataport <cik> (--format=binary|boolean|float|integer|string) [--name=<name>]
  exo [options] create-client <cik> [--name=<name>]
  exo [options] map <cik> <rid> <alias>
  exo [options] drop <cik> <rid>
  exo [options] listing <cik> (--type=client|dataport|datarule|dispatch) ...
  exo [options] info <cik> <rid> [--cikonly]
  exo [options] tree <cik> [--show-rid] [--show-aliases]

Options:
  -h --help            Show this screen.
  -v --version         Show version.
  --host=<host>        OneP URL. Default is $EXO\_HOST or m2.exosite.com.
  --httptimeout=<sec>  HTTP timeout setting.
  --pretty             Pretty print output
```

```
    $ ./exodata -h

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

## Examples

For usage examples, see examples/.

