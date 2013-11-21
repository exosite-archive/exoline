History
=======

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

