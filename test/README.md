Exoline Tests
=============

To run Exoline tests, copy test/testconfig.py.template to test/testconfig.py and set the 'portalcik' to the CIK of a portal that can be used for test. test.py will create several devices in that portal, run some tests, and then drop them.

```
    $ cd test
    $ pip install -r requirements.txt
    $ cd ..
    $ # run full set of tests in standard set of python versions
    $ ./test.sh
    $ # run full set of tests with a specific python version
    $ ./test.sh -e py27
    $ # run one test against a specific python version
    $ ./testone.sh update_test -e py27
    $ # run tests matching attributes 
    $ # attributes are specified with the attr decorator, e.g.:
    $ # @attr('script')
    $ # def script_test(self):
    $ ./testattr.sh "spec and not script"
```
