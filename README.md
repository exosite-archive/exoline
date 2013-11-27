Exoline: Exosite Command Line
=============================

Exoline is command line tool for working with the Exosite [One Platform](http://exosite.com/products/onep).  

Installation 
------------

To install the latest released version of Exoline from PyPI:

```bash

    $ pip install exoline
```

Alternatively, you can install from source:

```bash

    $ git clone git://github.com/exosite/exoline
    $ cd exoline
    $ python setup.py install
```

Depending on your Python environment, you may need to run the above install commands as sudo. You can avoid this by installing locally:

```bash

    $ pip install --user exoline
```

[virtualenvwrapper](http://virtualenvwrapper.readthedocs.org/en/latest/) is a great way to manage Python environments and avoid needing to use sudu for package installs.

Exoline currently supports Python 2.6 and 2.7.

Installation - Windows
----------------------

To install Exoline to a Windows machine that does not already have Python, follow these instructions first.

Install [Python](http://www.python.org/getit/).

Install [setuptools](https://pypi.python.org/pypi/setuptools).

Install [pip](https://pypi.python.org/pypi/pip).

Then follow the standard installation instructions above (`pip install exoline`).


Usage
-----

```

$ exo --help
Exosite RPC API Command Line Interface
   Provides command line access to the Remote Procedure Call API:
   https://github.com/exosite/api/tree/master/rpc

Usage:
  exo [--help] [options] <command> [<args> ...]

Commands:
  read     Read data from a resource.
  write    Write data at the current time.
  record   Write data at a specified time.
  create   Create a resource from a json description passed on stdin,
           or using reasonable defaults.
  listing  List the RIDs of a client's children.
  info     Get metadata for a resource in json format.
  update   Update a resource from a json description passed on stdin.
  map      Add an alias to a resource.
  unmap    Remove an alias from a resource.
  lookup   Look up a resource's RID based on its alias or cik.
  drop     Drop (permanently delete) a resource.
  flush    Remove all time series data from a resource.
  usage    Display usage of One Platform resources over a time period.
  tree     Display a resource's descendants.
  script   Upload a Lua script
  spark    Show distribution of intervals between points.
  copy     Make a copy of a client.
  diff     Show differences between two clients.
  ip       Get IP address of the server.
  data     Read or write with the HTTP Data API.
  spec     Determine whether a client matches a specification (beta)

Options:
  --host=<host>        OneP URL. Default is $EXO_HOST or m2.exosite.com
  --port=<port>        OneP port. Default is $EXO_HOST or 443
  --httptimeout=<sec>  HTTP timeout [default: 60]
  --https              Enable HTTPS (deprecated, HTTPS is default)
  --http               Disable HTTPS
  --debug              Show info like stack traces
  --debughttp          Turn on debug level logging in pyonep
  --discreet           Obfuscate RIDs in stdout and stderr
  -h --help            Show this screen
  -v --version         Show version

See 'exo <command> --help' for more information on a specific command.
```

Examples
--------

Show a tree view of a client

```bash
$ exo --discreet tree 5de0cfcf7b5bed2ea7a801234567890123456789
Dev client cik: 5de0cfcf7b5bed2ea7a801234567890123456789 (aliases: (see parent))
  ├─device1 client cik: 970346d3391a2d8c703a01234567890123456789 (aliases: [u'device1'])
  └─device2 client cik: e95052ab56f985e6807d01234567890123456789 (aliases: [u'device2'])
      └─json string dataport rid: 82209d5888a3bd1530d201234567890123456789 (aliases: [u'json'])

```

Upload a Lua script

```bash

    $ exo script translate_gps.lua e469e336ff9c8ed9176bc05ed7fa40daaaaaaaaa     
    Updated script RID: 6c130838e14903f7e12d39b5e76c8e3aaaaaaaaa
```

Monitor output of a script

```bash

    $ exo read e469e336ff9c8ed9176bc05ed7fa40daaaaaaaaa translate_gps.lua --follow 
    2013-07-09 11:57:45,line 2: Running translate_gps.lua...
    2013-07-09 12:00:17,"line 12: New 4458.755987,N,09317.538945,W
    line 23: Writing 4458.755987_-09317.538945"
    2013-07-09 12:15:41,"line 12: New 4458.755987,N,09317.538945,W
    line 23: Writing 4458.755987_-09317.538945"
```

Write raw data

```bash

    $ exo write e469e336ff9c8ed9176bc05ed7fa40daaaaaaaa gps-raw --value=4458.755987,N,09317.538945,W
```

Record a bunch of data without timestamps

```bash

    $ cat myrawgps | exo record e469e336ff9c8ed9176bc05ed7fa40daaaaaaaaa gps-raw - 
```

Dump data from multiple dataports to CSV

```bash

    $ time ./exo.py read 2ca4f441538c1f2cc8bfaaaaaaaaaaaaaaaaaaaa gas temperature humidity event --start=5/1/2013 --end=8/1/2013 --chunkhours=24 > alldata.csv

    real    1m58.377s
    user    0m10.981s
    sys     0m0.506s

    $ wc -l alldata.csv
      316705 alldata.csv
```

Make a copy of a device

```bash

    $ exo copy e469e336ff9c8ed9176bc05ed7fa40daaaaaaaaa ed6c3facb6a3ac68c4de9a6996a89594aaaaaaaa
    cik: c81e6ae0fbbd7e9635aa74053b3ab6aaaaaaaaaa
```

Create a new client or resource

```bash

    $ ../exoline/exo.py create ad02824a8c7cb6b98fdfe0a9014b3c0faaaaaaaa --type=dataport --format=string --name=NewString
    rid: 34eaae237988167d90bfc2ffeb666daaaaaaaaaa
```

Show differences between two clients

```bash

    $ exo copy 3ae52bdd5280d7cb96a2077b0cd5aaaaaaaaaaaa 5de0cfcf7b5bed2ea7a802ebe0679baaaaaaaaaa
    cik: cc080a86b1c9b53d5371e0fa793faaaaaaaaaaa
    $ exo diff 3ae52bdd5280d7cb96a2077b0cd5aaaaaaaaaaaa cc080a86b1c9b53d5371e0fa793f1daaaaaaaaaa
    $ exo create cc080a86b1c9b53d5371e0fa793f1aaaaaaaaaaa --type=dataport --format=float --name=Humidity
    rid: 6a8974d3d7d1f0ffd28385c90a1bebaaaaaaaaaa
    $ ../exoline/exo.py diff 3ae52bdd5280d7cb96a2077b0cd5dbaaaaaaaaaa cc080a86b1c9b53d5371e0fa793f1daaaaaaaaaa
    {
        "<<RID>>": {
        "aliases": {
            "<<RID>>": [
            "temp"
            ]
        }, 
        "basic": {
            "subscribers": 0, 
            "type": "client"
        }, 
        "children": {
            "<<RID>>": {
    +         "basic": {
    +           "subscribers": 0, 
    +           "type": "dataport"
    +         }, 
    +         "children": {}, 
    +         "comments": [], 
    +         "description": {
    +           "format": "float", 
    +           "meta": "", 
    +           "name": "Humidity", 
    +           "preprocess": [], 
    +           "public": false, 
    +           "retention": {
    +             "count": "infinity", 
    +             "duration": "infinity"
    +           }, 
    +           "subscribe": null
    +         }, 
    +         "shares": [], 
    +         "subscribers": [], 
    +         "tags": []
    +       }, 
    +       "Temperature.f2a40b81cb677401dffdc2cfad0f8a266d63590b": {
            "basic": {
                "subscribers": 0, 
                "type": "dataport"
            }, 
            "children": {}, 
            "comments": [], 
            "description": {
                "format": "float", 
                "meta": "", 
                "name": "Temperature", 
                "preprocess": [], 
                "public": false, 
                "retention": {
                "count": "infinity", 
                "duration": "infinity"
                }, 
                "subscribe": null
            }, 
            "shares": [], 
            "subscribers": [], 
            "tags": []
            }
        }, 
        "comments": [], 
        "counts": {
            "client": 0, 
    -       "dataport": 1, 
    ?                   ^
    +       "dataport": 2, 
    ?                   ^
            "datarule": 0, 
            "dispatch": 0
        }, 
        "description": {
            "limits": {
            "client": "inherit", 
            "dataport": "inherit", 
            "datarule": "inherit", 
            "disk": "inherit", 
            "dispatch": "inherit", 
            "email": "inherit", 
            "email_bucket": "inherit", 
            "http": "inherit", 
            "http_bucket": "inherit", 
            "share": "inherit", 
            "sms": "inherit", 
            "sms_bucket": "inherit", 
            "xmpp": "inherit", 
            "xmpp_bucket": "inherit"
            }, 
            "locked": false, 
            "meta": "", 
            "name": "MyDevice", 
            "public": false
        }, 
        "shares": [], 
        "subscribers": [], 
        "tagged": [], 
        "tags": []
        }
    }
```

See the HTTP requests and responses being made by pyonep:

```bash

$ exo --debughttp --discreet read <cik> temperature
DEBUG:pyonep.onep:POST /api:v1/rpc/process
Host: m2.exosite.com:80
Headers: {'Content-Type': 'application/json; charset=utf-8'}
Body: {"calls": [{"id": 70, "procedure": "read", "arguments": [{"alias": "temperature"}, {"sort": "desc", "selection": "all", "limit": 1, "endtime": 1376943416, "starttime": 1}]}], "auth": {"cik": "2ca4f441538c1f2cc8bf01234567890123456789"}}
DEBUG:pyonep.onep:HTTP/1.1 200 OK
Headers: [('date', 'Mon, 19 Aug 2013 20:16:53 GMT'), ('content-length', '54'), ('content-type', 'application/json; charset=utf-8'), ('connection', 'keep-alive'), ('server', 'nginx')]
Body: [{"id":70,"status":"ok","result":[[1376819736,24.1]]}]
2013-08-18 04:55:36,24.1
```


Environment Variables
---------------------

For convenience, several command line options may be replaced by environment variables.

* EXO\_HOST: host, e.g. m2.exosite.com. This supplies --host to exo and --url for exodata.
* EXO\_PORT: port, e.g. 80. Currently this only applies to exo, not exodata.


CIK Shortcuts
-------------

Store your commonly used CIKs in a file:

```bash

$ printf "keys:\n" > ~/.exoline
$ printf "    foo: 2ca4f441538c1f2cc8bf01234567890123456789\n" >> ~/.exoline
$ exo read foo temperature
2013-08-18 04:55:36,24.1
```

Help 
----

For help, run each command with -h from the command line.


Usage as a Library
------------------

Exoline can be directly imported and used in Python as a library. There are two patterns 
for doing this. First, you can call `exo.run` with whatever arguments you would have 
passed on the command line, plus an optional string stdin parameter.

```python

from exoline import exo

result = exo.run(['exo', 
                  'script', 
                  'scripts/myscript.lua', 
                  'ad02824a8c7cb6b98fdfe0a9014b3c0faaaaaaaa'])

print(result.exitcode)    # 0
print(result.stdout)      # Updated script RID: c9c6daf83c44e44985aa724fea683f14eda71fac
print(result.stderr)      # <no output> 
```

It's also possible to use Exoline's wrapper for the pyonep library, which covers a lot of
Exoline's functionality.

```python

from exoline import exo

rpc = exo.ExoRPC()
 
rpc.upload_script(ciks=['ad02824a8c7cb6b98fdfe0a9014b3c0faaaaaaaa'], 
                  filename='scripts/myscript.lua')
```


Issues/Feature Requests
-----------------------

If you see an issue with exoline or want to suggest an improvement, please log it [here](https://github.com/exosite/exoline/issues).


Test
----

To run the tests, install the packages in test/requirements.txt, and then type:

```bash

    $ cd test
    $ source test.sh
```

Version History
---------------

For information about what features are in what Exoline versions look [here](HISTORY.md).


TODO
----

- copy command should support taking input from stdin (which would be the ouput of info --recursive)
- investigate copying resources with public: True to destination with public: False (One Platform error: restricted)
- clarify what the first and second parameter to copy need to be. Maybe require explicit --device= and --portal= They could be anything, but 95% of the time the first param will be a device CIK, the second a portal CIK.
- --name parameter to copy command so names don't conflict
- --desconly parameter for info command, to show info as json so it can be piped to create
- add raw command, taking full RPC json from stdin
- Make the info command take multiple rids (or stdin)
- delete serial number when dropping device
- add --howmany option to create command
- tab completion for commands and shortcuts
- add create command shorthand: "exo create float foo" to create a dataport of format float with alias and name both set to foo
- add create clone support
- add test for --tz option
- add support for Portals cache invalidation: --portals to turn on cache invalidation, --portals_host to set the portals host
  per: https://i.exosite.com/display/DEVPORTALS/Portals+Cache+Invalidation+API
- add the option of using requests to authenticate with https (see warning here: http://docs.python.org/2/library/httplib.html)
- add windows executable to build and test
