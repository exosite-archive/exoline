TEST=$1
shift
tox $@ -- test/test.py:TestRPC.$TEST
