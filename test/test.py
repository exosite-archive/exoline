"""Exoline test
   Tests exoline commands. Requires portalcik to be set in config.py.

Usage:
  test.py <portal-cik>
"""
import sys
import json
import re
import time
import StringIO
import logging
from unittest import TestCase

from ..exoline import exo

try:
    from testconfig import config
except:
    sys.stderr.write(
        "Please copy testconfig.py.template to testconfig.py and set portalcik.")


class CmdResult():
    def __init__(self, exitcode, stdout):
        self.exitcode = exitcode
        self.stdout = stdout

logging.basicConfig(stream=sys.stderr)
logging.getLogger("TestRPC").setLevel(logging.DEBUG)
logging.getLogger("_cmd").setLevel(logging.DEBUG)
log = logging.getLogger("_cmd")

def _cmd(argv, stdin, stdout):
    '''Runs an exoline command, translating stdin from
    string and stdout to string. Returns a CmdResult.'''
    if False:
        log.debug("argv: {}, stdin: {}, stdout: {}".format(
            argv, stdin, stdout))
    if type(stdin) is str:
        sio = StringIO.StringIO()
        sio.write(stdin)
        sio.seek(0)
        stdin = sio
    stdout = StringIO.StringIO()

    # unicode causes problems in docopt
    argv = [str(a) for a in argv]
    exitcode = exo.cmd(argv=argv, stdin=stdin, stdout=stdout)

    stdout.seek(0)
    stdout = stdout.read()
    if exitcode != 0:
        log.debug("Exit code was {}".format(exitcode))
    return CmdResult(exitcode, stdout)

def rpc(*args, **kwargs):  # stdin=None, stdout=None):
    #log.debug(args)
    #log.debug(kwargs)
    stdin = kwargs.get('stdin', None)
    stdout = kwargs.get('stdout', None)
    return _cmd(['exo'] + list(args), stdin=stdin, stdout=stdout)


class Resource():
    '''Contains information for creating and testing resource.'''
    def __init__(self, parentcik, type, desc, write=None, record=None):
        self.parentcik = parentcik
        self.type = type
        self.desc = desc
        self.write = write
        self.record = record
        self.rid = None
        if self.type == 'dataport':
            self.desc['retention'] =  {"count": "infinity", "duration": "infinity"}
            self.desc['public'] = False

    def created(self, rid, info):
        self.rid = rid
        self.info = info

    def cik(self):
        return self.info['key']


class TestRPC(TestCase):
    # test client
    cl = None

    def _rid(self, s):
        '''Parse rid from s, raising an exception if it doesn't validate.'''
        m = re.match("^([a-zA-Z0-9]{40}).*", s)
        self.assertFalse(m is None, "rid: {}".format(s))
        return str(m.groups()[0])

    def _create(self, res):
        '''Creates a resource at the command line.'''
        r = rpc('create', res.parentcik, '--type=' + res.type, '-',
                stdin=json.dumps(res.desc))
        rid = self._rid(r.stdout)
        r = rpc('info', res.parentcik, rid)
        info = json.loads(r.stdout.strip())
        res.created(rid, info)
        self.l("Created {}, rid: {}".format(res.type, res.rid))
        return res

    def l(self, s):
        self.log.debug(s)

    def setUp(self):
        '''Create some devices in the portal to test'''
        self.log = logging.getLogger("TestRPC")
        self.portalcik = config['portalcik']
        self.client = Resource(
                self.portalcik,
                'client',
                {'limits': {'dataport': 'inherit',
                           'datarule': 'inherit',
                           'dispatch': 'inherit',
                           'disk': 'inherit',
                           'io': 'inherit'},
                'writeinterval': 'inherit',
                "name": "testclient",
                "visibility": "parent"})
        self._create(self.client)

        # test details for create, read, and write tests.
        self.resources = [
            Resource(
                self.client.cik(),
                'dataport',
                {'format': 'integer', 'name': 'int_port'},
                write=['-1', '0', '100000000'],
                record=[[665366400, 42]]),
            Resource(
                self.client.cik(),
                'dataport',
                {'format': 'boolean', 'name': 'boolean_port'},
                write=['false', 'true', 'false']),
            Resource(
                self.client.cik(),
                'dataport',
                {'format': 'string', 'name': 'string_port'},
                write=['test', 'a' * 300]),
            Resource(
                self.client.cik(),
                'dataport',
                 {'format': 'float', 'name': 'float_port'},
                 write=['-0.1234567', '0', '3.5', '100000000.1']),
                # TODO: handle scientific notation from OneP '-0.00001'
            Resource(
                self.client.cik(),
                'dataport',
                 {'format': 'binary', 'name': 'binary_port'})
            ]

        for res in self.resources:
            self._create(res)
            # test that description is contains what we asked for
            for k, v in res.desc.iteritems():
                self.assertTrue(res.info['description'][k] == v)

    def tearDown(self):
        '''Clean up any test client'''
        rpc('drop', self.portalcik, self.client.rid)

    def _writeAndRead(self, res):
        if res.write is not None:
            cik = res.parentcik
            rid = res.rid
            for value in res.write:
                r = rpc('write', cik, rid, '--value=' + value)
                time.sleep(1)

            r = rpc('read', cik, rid, '--limit={}'.format(len(res.write)))
            wroteValues = [unicode(v) for v in res.write]
            lines = r.stdout.split('\n')
            readValues = [line.split(',')[1].strip()
                          for line in lines if len(line.strip()) > 0]
            readValues.reverse()
            self.l('Wrote {}'.format(wroteValues))
            self.l('Read {}'.format(readValues))
            self.assertTrue(wroteValues == readValues)

    def _recordAndRead(self, res):
        pass

    def readwrite_dataport_test(self):
        '''Write to and read from dataports'''
        for res in self.resources:
            if res.type == 'dataport':
                # test writing
                self._writeAndRead(res)

                # test recording
                #yield self._recordAndRead, rt
