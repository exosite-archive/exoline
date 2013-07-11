History
=======

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

