Exoline Tests
=============

Test exoline.

Usage
-----

First, copy testconfig.py.template to testconfig.py and set the 'portalcik' to the CIK of a portal that can be used for test. test.py will create several devices in that portal, run some tests, and then drop them.

```bash

    $ source test.sh
```

To run a specific test:

```bash

    $ nosetests test.py:TestRPC.record_test
    $ # or
    $ ./testone.sh record_test
```



To run full tests against multiple python distributions:

```bash

    $ source test.sh full
```

If the PyYAML build warnings drive you crazy (as they do me), you can do this:

```bash

    $ source test.sh full --quiet
```
