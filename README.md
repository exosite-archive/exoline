# Exoline - Exosite Command Line

Exoline provides a command line interface (CLI) for accessing Exosite.

exo - CLI for the [RPC API](http://developers.exosite.com/display/OP/Remote+Procedure+Call+API)
exodata - CLI for the [HTTP Data Interface API](http://developers.exosite.com/display/OP/HTTP+Data+Interface+API)

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


## Run 

1. Run tests:

    $ cd portals
    $ python test.pyxoline

## Examples

For usage examples, see examples/.

