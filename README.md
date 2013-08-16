Exoline: Exosite Command Line
=============================

Exoline is a set of commands for accessing the Exosite [One Platform](http://exosite.com/products/onep) from the command line.  

- **exo** - command for the [RPC API](http://developers.exosite.com/display/OP/Remote+Procedure+Call+API) 
- **exodata** - command for the [HTTP Data Interface API](http://developers.exosite.com/display/OP/HTTP+Data+Interface+API) 

Installation 
------------

To install the latest released version of exoline from PyPI:

```bash

    $ pip install exoline
```

Alternatively, you can install from source:

```bash

    $ git clone git://github.com/dweaver/exoline
    $ cd exoline
    $ python setup.py install
```

Depending on your python environment, you may need to run the above install commands as sudo. [virtualenvwrapper](http://virtualenvwrapper.readthedocs.org/en/latest/) is a great way to keep your python environment clean, and has the side-effect that you don't need to use sudo when installing python packages.

Examples
--------

Here are a few things you can do with Exoline.

* Show a tree view of a client

```bash

$ exo tree 5de0cfcf7baaaaaaaaaaaaaaaaaaaaaaaaaaaaaa --hide-keys
cik: 5de0cfcf7baaaaaaaaaaaaaaaaaaaaaaaaaaaaaa (client name: Dev, aliases: (see parent), count: 1088)
  ├─cik: 173a087812aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa (client name: testclient, rid: 6de3fd516faaaaaaaaaaaaaaaaaaaaaaaaaaaaaa, count: 1)
  │   ├─rid: 097fea31e0aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa (dataport name: int_port, format: integer, count: 0)
  │   ├─rid: a0e62edd21aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa (dataport name: boolean_port, format: boolean, count: 0)
  │   ├─rid: b005167070aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa (dataport name: float_port, format: float, count: 0)
  │   └─rid: f9f21bc8ceaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa (dataport name: string_port, format: string, aliases: [u'newalias', u'string_port_alias'], count: 0)
  └─cik: c81e6ae0fbaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa (client name: Sally, rid: dec8dedcc1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa, count: 2)
      ├─rid: e84b7cb6cbaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa (dataport name: anothertest, format: string, count: 0)
      └─cik: bed592d350aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa (client name: George, rid: 7f94e98943aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa, count: 2)
          ├─cik: e0b93720eeaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa (client name: MrFlippy, aliases: [u'bedchild'], count: 1)
          │   └─cik: fa3cdb81e2aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa (client name: LemonJello, rid: 4f9ff15a52aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa, count: 4)
          │       ├─rid: 1043eabc31aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa (dataport name: inttest, format: integer, count: 0)
          │       ├─rid: 59b7b90ac2aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa (dataport name: strtest, format: string, count: 0)
          │       ├─rid: 616749f6ddaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa (dataport name: bintest, format: binary, count: 0)
          │       └─rid: 7b7a3bcc36aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa (datarule name: test.lua, format: string, aliases: [u'test.lua'], count: 1)
          └─cik: ed6c3facb6aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa (client name: Mack, rid: cbc55a2e06aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa, count: 1)
              └─rid: 1b62533276aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa (datarule name: test.lua, format: string, aliases: [u'test.lua'], count: 1)
```

* Upload a Lua script

```bash

    $ exo script translate_gps.lua e469e336ff9c8ed9176bc05ed7fa40daaaaaaaaa     
    Updated script RID: 6c130838e14903f7e12d39b5e76c8e3aaaaaaaaa
```

* Monitor output of a script

```bash

    $ exo read e469e336ff9c8ed9176bc05ed7fa40daaaaaaaaa translate_gps.lua --follow 
    2013-07-09 11:57:45,line 2: Running translate_gps.lua...
    2013-07-09 12:00:17,"line 12: New 4458.755987,N,09317.538945,W
    line 23: Writing 4458.755987_-09317.538945"
    2013-07-09 12:15:41,"line 12: New 4458.755987,N,09317.538945,W
    line 23: Writing 4458.755987_-09317.538945"
```

* Write raw data

```bash

    $ exo write e469e336ff9c8ed9176bc05ed7fa40daaaaaaaaa gps-raw --value=4458.755987,N,09317.538945,W
```

* Record a bunch of data without timestamps

```bash

    $ cat myrawgps | exo record e469e336ff9c8ed9176bc05ed7fa40daaaaaaaaa gps-raw - 
```

* Dump data from multiple dataports to CSV

```bash

    $ time ./exo.py read 2ca4f441538c1f2cc8bfaaaaaaaaaaaaaaaaaaaa gas temperature humidity event --start=5/1/2013 --end=8/1/2013 --chunkhours=24 > alldata.csv

    real    1m58.377s
    user    0m10.981s
    sys     0m0.506s

    $ wc -l alldata.csv
      316705 alldata.csv
```

* Make a copy of a device

```bash

    $ exo copy e469e336ff9c8ed9176bc05ed7fa40daaaaaaaaa ed6c3facb6a3ac68c4de9a6996a89594aaaaaaaa
    cik: c81e6ae0fbbd7e9635aa74053b3ab6aaaaaaaaaa
```

* Create a new client or resource

```bash

    $ ../exoline/exo.py create ad02824a8c7cb6b98fdfe0a9014b3c0faaaaaaaa --type=dataport --format=string --name=NewString
    rid: 34eaae237988167d90bfc2ffeb666daaaaaaaaaa
```

* Show differences between two clients

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

Environment Variables
---------------------

For convenience, several command line options may be replaced by environment variables.

* EXO\_HOST: host, e.g. m2.exosite.com. This supplies --host to exo and --url for exodata.
* EXO\_PORT: port, e.g. 80. Currently this only applies to exo, not exodata.



Help 
----

For help, run each command with -h from the command line.



Test
----

To run the tests, install the packages in test/requirements.txt, and then type:

```bash

    $ cd test
    $ source test.sh
```

TODO
----

- copy command should support taking input from stdin (which would be the ouput of info --recursive)
- investigate copying resources with public: True to destination with public: False (One Platform error: restricted)
- clarify what the first and second parameter to copy need to be. Maybe require explicit --device= and --portal= They could be anything, but 95% of the time the first param will be a device CIK, the second a portal CIK.
- --name parameter to copy command so names don't conflict
- --desconly parameter for info command, to show info as json so it can be piped to create
- add raw command, taking full RPC json from stdin
- add key command for making local CIK aliases/shortcuts (with tab completion for shortcuts?)
- Make the info command take multiple rids (or stdin)
- delete serial number when dropping device
- add a --verbose option that logs complete requests and response bodies
- add --howmany option to create command
- tab completion for commands
