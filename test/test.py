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
        "Copy testconfig.py.template to testconfig.py and set portalcik.")


class CmdResult():
    def __init__(self, exitcode, stdout):
        self.exitcode = exitcode
        self.stdout = stdout

logging.basicConfig(stream=sys.stderr)
logging.getLogger("TestRPC").setLevel(logging.DEBUG)
logging.getLogger("_cmd").setLevel(logging.DEBUG)
log = logging.getLogger("_cmd")


def _cmd(argv, stdin):
    '''Runs an exoline command, translating stdin from
    string and stdout to string. Returns a CmdResult.'''
    if True:
        log.debug(' '.join(argv))
        if stdin is not None:
            log.debug('    stdin: ' + stdin)
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
    stdout = stdout.read().strip()  # strip to get rid of leading newline
    if exitcode != 0:
        log.debug("Exit code was {}".format(exitcode))
    return CmdResult(exitcode, stdout)


def rpc(*args, **kwargs):
    stdin = kwargs.get('stdin', None)
    return _cmd(['exo'] + list(args), stdin=stdin)


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
            self.desc['retention'] = {"count": "infinity",
                                      "duration": "infinity"}
            self.desc['public'] = False

    def created(self, rid, info):
        self.rid = rid
        self.info = info

    def cik(self):
        return self.info['key']


class TestRPC(TestCase):
    def _rid(self, s):
        '''Parse rid from s, raising an exception if it doesn't validate.'''
        m = re.match("^([a-zA-Z0-9]{40}).*", s)
        self.assertFalse(m is None, "rid: {}".format(s))
        return str(m.groups()[0])

    def _create(self, res):
        '''Creates a resource at the command line.'''
        r = rpc('create',
                res.parentcik,
                '--type=' + res.type,
                '--ridonly',
                '-',
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
                record=[[665366400, '42']]),
            Resource(
                self.client.cik(),
                'dataport',
                {'format': 'boolean', 'name': 'boolean_port'},
                write=['false', 'true', 'false'],
                record=[[-100, 'true'], [-200, 'false'], [-300, 'true']]),
            Resource(
                self.client.cik(),
                'dataport',
                {'format': 'string', 'name': 'string_port'},
                write=['test', 'a' * 300],
                record=[[163299600, 'home brew'], [543212345, 'nonsense']]),
            Resource(
                self.client.cik(),
                'dataport',
                {'format': 'float', 'name': 'float_port'},
                write=['-0.1234567', '0', '3.5', '100000000.1'],
                record=[[-100, '-0.1234567'], [-200, '0'], [-300, '3.5'], [-400, '10000000.1']]),
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

    def _readBack(self, res, limit):
        r = rpc('read',
                res.parentcik,
                res.rid,
                '--limit={}'.format(limit),
                '--timeformat=unix')
        lines = r.stdout.split('\n')
        vread = []
        for line in lines:
            t, v = line.split(',')
            t = int(t)
            if v.endswith('\r'):
                v = v[:-1]
            vread.append([t, v])
        vread.reverse()
        return vread

    def _verifyWrite(self, wrotevalues, readvalues):
        readvalues_notime = [v[1] for v in readvalues]
        self.l('Wrote {}'.format(wrotevalues))
        self.l('Read  {}'.format(readvalues))
        self.assertTrue(wrotevalues == readvalues_notime,
                        'Read values did not match written values')

    def write_test(self):
        '''Write to dataports'''
        for res in self.resources:
            if res.type == 'dataport' and res.write is not None:
                # test writing
                if res.write is not None:
                    cik = res.parentcik
                    rid = res.rid
                    for value in res.write:
                        rpc('write', cik, rid, '--value=' + value)
                        time.sleep(1)

                    readvalues = self._readBack(res, len(res.write))
                    self._verifyWrite(res.write, readvalues)


    def _verifyRecord(self, writetime, wrotevalues, readvalues):
        '''Checks readvalues against wrotevalues and returns True if they match
        or False if they don't. This function is complicated because wrotevalues
        could include negative timestamps, which are recorded relative to the
        current time and since we don't know the time when they were recorded,
        we can only compare within a margin.'''
        errsec = 5          # negative timestamp can be this many seconds off

        # turn timestamps into tuples of (timestamp, allowed_err)
        # and sort them based on timestamp. So wv_err might look like, e.g.:
        # [[(665366400, 0), "Hello"], [(665370000, 10), "World"]]

        wv_errors = []
        err = 5  # +/- error for negative timestamps
        for t, v in wrotevalues:
            if t >= 0:
                wv_errors.append([(t, 0), v])
            else:
                wv_errors.append([(writetime + t, err), v])
        wv_errors = sorted(wv_errors, key=lambda x: x[0][0])

        # compare arrays
        self.l('Wrote     {}'.format(wrotevalues))
        self.l('wv_errors {}'.format(wv_errors))
        self.l('Read      {}'.format(readvalues))
        if len(readvalues) != len(wrotevalues):
            return False
        for ((wt, terr), wv), (rt, rv) in zip(wv_errors, readvalues):
            if wt >= 0:
                if wt != rt or wv != rv:
                    return False
            else:
                approxt = int(writetime) + wt
                if rt < approxt - errsec or approxt + errsec < rt or wv != rv:
                    return False
        return True


    def record_test(self):
        '''Record to dataports'''
        def _recordAndVerify(res, recordfn):
            if res.record is not None:
                writetime = int(time.time())
                recordfn(res)
                readvalues = self._readBack(res, len(res.record))
                self._verifyRecord(writetime, res.record, readvalues)

        def _flush(res):
            rpc('flush', res.parentcik, res.rid)

        def one_by_one(res):
            for timestamp, value in res.record:
                r = rpc('record',
                        res.parentcik,
                        res.rid,
                        '--value={},{}'.format(timestamp, value))
                self.assertTrue(r.exitcode == 0)
                time.sleep(1)

        def one_line(res):
            r = rpc('record',
                    res.parentcik,
                    res.rid,
                    *['--value={},{}'.format(t, v) for t, v in res.record])
            self.assertTrue(r.exitcode == 0)

        def on_stdin(res):
            r = rpc('record',
                    res.parentcik,
                    res.rid,
                    '-',
                    stdin='\n'.join(['{},{}'.format(t, v) for t, v in res.record]))
            self.assertTrue(r.exitcode == 0)

        for r in self.resources:
            if r.type == 'dataport':
                _recordAndVerify(r, one_by_one)
                _flush(r)
                _recordAndVerify(r, one_line)
                _flush(r)
                _recordAndVerify(r, on_stdin)
                _flush(r)

    def tree_test(self):
        '''Tree command'''
        cik = self.client.cik()
        r = rpc('tree', cik)
        # call did not fail
        self.assertTrue(r.exitcode == 0)
        # starts with cik
        self.l(r.stdout)
        self.assertTrue(re.match("cik: {}.*".format(cik), r.stdout) is not None)
        # has correct number of lines
        self.assertTrue(len(r.stdout.split('\n')) == len(self.resources) + 1)
