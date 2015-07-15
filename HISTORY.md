History
=======

0.9.18 (2015-07-15)
-------------------

- support client limits in spec (device.limits)
- support spec files without resources
- re-add support for Python 2.6 by switching to 
  dotenv from python-dotenv (run pip uninstall 
  python-dotenv to upgrade from 0.9.17)
- fix extraneous output from search
- document tab completion and .env

0.9.17 (2015-07-14)
-------------------

- fix issue where spec would not update public, subscribe, 
  preprocess, retention
- support [tab completion](https://github.com/exosite/exoline/blob/master/exoline/complete.sh)
- support .env
- temporarily drop support for Python 2.6

0.9.16 (2015-05-29)
-------------------

- add spec support for dispatches and datarules

0.9.15 (2015-05-11)
-------------------

- find command (beta)
- script --version string to store version in meta
- fix assertion in tree/twee when resource and its
  share have the same parent. In this case, only show
  the original.

0.9.14 (2015-05-01)
-------------------

- add --follow option for attractive script logs
- warn if a script is >16k
- warn that script will not be restarted if code was unchanged

0.9.13 (2015-04-29)
-------------------

- work around for read --follow wait issue for script logs

0.9.12 (2015-04-28)
-------------------

- spec command support for operating on expired devices

0.9.11 (2015-04-03)
-------------------

- make read --follow faster by using wait() API
- support integer cik shortcuts in Exoline config
- bump up versions of package dependencies

0.9.10 (2015-03-11)
-------------------

- spec --create support for preprocess updates

0.9.9 (2014-02-26)
------------------

- update to pyonep 0.11.0

0.9.8 (2014-02-23)
------------------

- list shares in tree and twee
- update for listing changes in pyonep 0.10.0

0.9.7 (2014-01-29)
------------------

- add --protected parameter to content put

0.9.6 (2014-01-08)
------------------

- fix string exitcode from in exo.run()

0.9.5 (2014-12-20)
------------------

- fix read --selection
- support relative time for --start and --end 
  (https://github.com/exosite/exoline/issues/30)
- added "did you mean..." suggestions for mistyped commands
- support url shorteners for spec scripts
- added chunking to record to handle large CSV files.
- added support to record for multiple RIDs as columns in a CSV 
- dump command to store a client hierarchy with data 
  to zip file 
- auths (CIKs) can contain a client or resource IDs as well.

0.9.4 (2014-12-03)
------------------

- fix pyonep version for Windows build
- update build machine to use 32-bit Python to run better on 
  32-bit Windows systems

0.9.3 (2014-12-02)
------------------

- add search command with support for name, alias, serial 
  number, script (https://github.com/exosite/exoline/issues/64)
- add globbing to the model, content, and sn list sub-commands
- makeShortcuts will create model#sn style shortcuts as well
- remove debug output and fix https://github.com/exosite/exoline/issues/62

0.9.2 (2014-11-24)
------------------

- spec accepts urls for yaml and script file
- support for putting lua directly in spec file "code"
  property instead of external lua file.
- spec --check option for rudimentary spec validation
- spec doesn't run if --check would fail

0.9.1 (2014-11-19)
------------------

- make model, content, and sn top-level commands
- write model, content, sn tests
- write usage documentation for provisioning
- many fixes to provision model and sn commands
- support --curl option for viewing requests in curl format
- added twee --rids option
- darker twee colors for visibility on white background

0.9.0 (2014-10-29)
------------------

- add provision command with support for activate, model, sn, content
- support read --timeformat=excel for spreadsheet import
- --config option to support multiple exoline config files
- fix using Exoline as a library in Python 3.4
- fix piping read - with unicode 
  (https://github.com/exosite/exoline/issues/48)
- show model name in twee output for clients
- script support for passing RID/alias of script
- (breaking change) remove CIK activation, to avoid confusion with 
  provision activate
- (breaking change) trim final newline from stdin for write -

0.8.3 (2014-10-20)
------------------

- Windows support for twee by disabling color

0.8.2 (2014-10-12)
------------------

- support retention in spec command
- support preprocess in spec command
- support subscribe in spec command
- makeShortcuts command for populating CIK shortcuts in .exoline
- flexible config file location 
- fix some unicode issues, add unicode tests
- fix exoline tree --values example output
- fix twee for dataports of type 'binary'

0.8.1 (2014-09-15)
------------------

- write command support for passing value on stdin
- --values option for tree to show latest point for dataports 
  and datarules
- add twee command: like tree, but more wuvable 
- make tree report and continue when it encounters locked clients
- fix tests that broke for float handling with OneP updates
- add standard script command order

0.8.0 (2014-06-09)
------------------

- transform command for modifying time series data
- EXO_PLUGIN_PATH variable to specify additional places to look for plugins 
- spec support for domain level schema updates 
- (breaking change) remove --chunkhours options and add --chunksize option,
  which usually does not need to be specified
- fixed Python 3.4 regression

0.7.14 (2014-05-30)
-------------------

- fix error in ExoRPC.mult()

0.7.13 (2014-05-28)
-------------------

- add ExoRPC.mult() to avoid calling \_exomult directly

0.7.12 (2014-05-28)
-------------------

- add --level option for info --recursive to limit depth

0.7.11 (2014-05-16)
-------------------

- Windows executable and installer
- fixed tree output for Windows

0.7.10 (2014-05-08)
-------------------

- add spec --portal option to apply a spec to multiple devices

0.7.9 (2014-04-15)
------------------

- tweak to tree output formatting
- better documentation for record - input
- upgrade pyonep

0.7.8 (2014-04-08)
------------------

- add support for JSON schema in spec command
- remove extraneous output from drop --all-children

0.7.7 (2014-04-02)
------------------

- update to latest pyonep
- fix RID regular expression

0.7.6 (2014-03-04)
------------------

- add clone command
- avoid partial copy when dataport subscribe is set

0.7.5 (2014-03-03)
------------------

- add --useragent param

0.7.4 (2014-02-04)
------------------

- if --start and --end are omitted to read, flush
  or usage, they are omitted from the RPC call. This 
  fixes an issue with read if clock is out of sync
  with One Platform.

0.7.3 (2014-01-31)
------------------

- add --start and --end for flush

0.7.2 (2014-01-14)
------------------

- add --generate option for spec command (beta)
- fix regression in tree command on python 3.2
- remove wsgiref to fix nose for python 3.3

0.7.1 (2014-01-13)
------------------

- handle unicode in csv output
- fix error when piping tree output to file 
- remove binary and boolean dataport formats

0.7.0 (2013-12-13)
------------------

- add share, activate, deactivate, and lookup --share commands
- listing command now accepts filtering options and clearer JSON 
  output (non-backward compatible)
- updates for incorrect timezone setting

0.6.1 (2013-12-10)
------------------

- add owner lookup command (lookup --owner-of)
- change "Options" to "Command Options" in usage

0.6.0 (2013-12-09)
------------------

- make portals server customizable, e.g., for use with sandbox

0.5.2 (2013-12-09)
------------------

- add --portals options and portals command for cache invalidation,
  so Portals and Exoline can stay in sync

0.5.1 (2013-12-02)
------------------

- support Python 3.x

0.5.0 (2013-11-21)
------------------

- remove --counts option to tree command
- remove storage option to the info command

0.4.3 (2013-11-19)
------------------

- make second parameter to exo.cmd optional
- restore std* so stdout is visible after calling exo.cmd()

0.4.2 (2013-11-13)
------------------

- spec command support for units and json format validation
- example spec file 

0.4.1 (2013-11-11)
------------------

- add activate command
- fix spec message for dataport format differences
- add documentation of spec command yaml syntax
- fix data write to handle urlencode characters (e.g. %)

0.4.0 (2013-10-30)
------------------

- use https by default, specify --http for http
- fix issue where read --follow could not be piped to other commands due to stdout buffering 
- show commands in a consistent order in 'exo --help' 
- show command summaries in 'exo --help'

0.3.6 (2013-10-29)
------------------

- read command defaults to reading all dataports/datarules if no RIDs are specified 
- listing command outputs valid JSON

0.3.5 (2013-10-28)
------------------

- reuse connection to speed up API calls

0.3.4 (2013-10-10)
------------------

- default to utc if local timezone can't be determined
- fix timezone bug in read output

0.3.3 (2013-10-4)
-----------------

- decode scripts as utf-8 for spec command

0.3.2 (2013-10-4)
-----------------

- remove plugin dependency on script install location

0.3.1 (2013-10-1)
-----------------

- fix install issue

0.3.0 (2013-9-30)
-----------------

- add plugin framework
- update tree output, incl. sort by client name
- add spec command as a plugin (beta)
- make listing default to all resource types
- timezone support for read command

0.2.6 (2013-9-19)
-----------------

- fixed update command

0.2.5 (2013-8-26)
-----------------

- record reads csv on stdin
- fixed read --sort=asc
- fixed --follow order when multiple values come within the polling window

0.2.4 (2013-8-19)
-----------------

- fixed combination of --debughttp and --discreet

0.2.3 (2013-8-19)
-----------------

- --debughttp shows http requests & responses
- --discreet hides ciks/rids
- documented usage as library

0.2.2 (2013-8-16)
-----------------

- --header option for read command

0.2.1 (2013-8-15)
-----------------

- cik lookup in ~/.exoline 
- support ISO8601 dates for read
- copy comments

0.2.0 (2013-8-13)
-----------------

- tree is faster for large portals
- --level option for tree
- copy checks limits when possible (when not set to 'inherit')
- improve json format for info --recursive

0.1.3 (2013-8-9)
----------------

- set up for automated testing in jenkins
- --include and --exclude flags for info 
- info and listing commands output json when using --pretty
- --recursive flag for script command
- fixed regression in read --follow

0.1.2 (2013-7-31)
-----------------

- added --port option
- added --chunkhours option to break up large reads

0.1.1 (2013-7-30)
-----------------

- fixed --httptimeout
- show model and serial number from metadata in tree output

0.1.0 (2013-7-24)
-----------------

- read from multiple data sources
- copy command (make a copy of a client)
- diff command (compare clients)
- --recursive option for info

0.0.33 (2013-7-19)
------------------

- support python 2.6

0.0.32 (2013-7-19)
-----------------

- lookup command looks up RID of CIK if no alias is passed
- fixed exception


0.0.31 (2013-7-18)
------------------

- updated to use pyonep 0.7.0
- added usage command

0.0.30 (2013-7-16)
------------------

- fixed regression in tree

0.0.29 (2013-7-16)
------------------

- fixed pyonep reference

0.0.28 (2013-7-16)
------------------

- usage command
- Better test coverage

0.0.27 (2013-7-14)
------------------

- Support uploading script to multiple CIKs
- Added code coverage for tests
- read --intervals shows the distribution of 
  delays between points

0.0.26 (2013-7-12)
------------------

- Fixed https port

0.0.25 (2013-7-12)
------------------

- Added --https flag

0.0.24 (2013-7-12)
------------------

- Added raw read format

0.0.23 (2013-7-12)
------------------

- Made <rid> optional for all commands
- Added root node detail output to tree

0.0.22 (2013-7-11)
------------------

- Bumped up version requirement for pyonep

0.0.21 (2013-7-11)
------------------

- Fixed tree output for devices with expired status
- Hide KeyboardInterrupt exception except when --debug set

0.0.20 (2013-7-10)
------------------

- Fixed script command

0.0.19 (2013-7-10)
------------------

- Fixed README.md

0.0.18 (2013-7-10)
------------------

- Help for individual commands, git style
- Fixed regression in 0.0.17 affecting all commands taking <rid>
- record-backdate is now record with --interval


0.0.17 (2013-7-09)
------------------

- Handle keyboard interrupt gracefully for read --follow
- Added example usage in README.md
- Fixed read --follow when dataport has no data

0.0.16 (2013-7-08)
------------------

- Support passing alias for <rid>
- Make read return latest value by default

0.0.15 (2013-7-08)
------------------

- script upload

0.0.14 (2013-7-07)
------------------

- tests for create, read, write

0.0.13 (2013-7-03)
------------------

- record, unmap, lookup commands, better/stronger/faster tree 

0.0.12 (2013-6-27)
------------------

- Show OnePlatform library exceptions nicely

0.0.11 (2013-6-27)
------------------

- Changed defaults for tree

0.0.10 (2013-6-27)
------------------

- flush command

0.0.9 (2013-6-26)
-----------------

- Added format to tree output


0.0.8 (2013-6-26)
-----------------

- Added units to tree output, support writing negative numeric values

0.0.7 (2013-6-23)
-----------------

- Time series data write and read commands, with --follow option


0.0.6 (2013-6-23)
-----------------

- RID lookup and bulk drop commands


0.0.5 (2013-6-21)
-----------------

- Install two command line scripts: exo, exodata


0.0.4 (2013-6-18)
-----------------

- Complete Exosite Data API
- Subset of Exosite RPC API

