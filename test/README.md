Exoline Tests
=============

To run Exoline tests,

1. Copy `test/testconfig.py.template` to `test/testconfig.py` and set the `'portalcik'` to the CIK of a portal that can be used for test. `test.py` will create a client as a child of this portal, and then it will create several devices in that portal, run some tests, and then drop them.
2. Follow the instructions [here](https://github.com/exosite/exoline#provisioning) to add your vendor ID and vendor name to your exoline configuration and to your `test/testconfig.py`
3. Install the test requirements with `pip install -r test/requirements.txt`

Here's what the different test-related scripts in the root directory do:

```
    $ # run one test against a specific python version
    $ ./testone.sh update_test -e py27
    $ # run full set of tests with a specific python version
    $ ./test.sh -e py27
    $ # run full set of tests in standard set of python versions
    $ ./test.sh
    $ # run tests matching attributes 
    $ # attributes are specified with the attr decorator, e.g.:
    $ # @attr('script')
    $ # def script_test(self):
    $ ./testattr.sh "spec and not script"
```

## Issues?

Occasionally package versions don't update correctly. Sometimes this helps:

```
$ rm -rf .tox
```
