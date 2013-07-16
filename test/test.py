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
    def __init__(self, exitcode, stdout, stderr):
        self.exitcode = exitcode
        self.stdout = stdout
        self.stderr = stderr

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
    stderr = StringIO.StringIO()

    # unicode causes problems in docopt
    argv = [str(a) for a in argv]
    exitcode = exo.cmd(argv=argv, stdin=stdin, stdout=stdout, stderr=stderr)

    stdout.seek(0)
    stdout = stdout.read().strip()  # strip to get rid of leading newline
    stderr.seek(0)
    stderr = stderr.read().strip()
    if exitcode != 0:
        log.debug("Exit code was {}".format(exitcode))
    return CmdResult(exitcode, stdout, stderr)


def rpc(*args, **kwargs):
    stdin = kwargs.get('stdin', None)
    return _cmd(['exo'] + list(args), stdin=stdin)


class Resource():
    '''Contains information for creating and testing resource.'''
    def __init__(self, parentcik, type, desc, write=None, record=None, alias=None):
        self.parentcik = parentcik
        self.type = type
        self.desc = desc
        self.write = write
        self.record = record
        self.rid = None
        self.alias = alias
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
    RE_RID = '[0-9a-f]{40}'
    def _rid(self, s):
        '''Parse rid from s, raising an exception if it doesn't validate.'''
        m = re.match("^({}).*".format(self.RE_RID), s)
        self.assertFalse(m is None, "rid: {}".format(s))
        return str(m.groups()[0])

    def _createMultiple(self, cik, resList):
        # use pyonep directly
        pyonep = exo.ExoRPC().exo
        for res in resList:
            pyonep.create(cik, res.type, res.desc, defer=True)

        rids = []
        # create resources
        if pyonep.has_deferred(cik):
            responses = pyonep.send_deferred(cik)
            for i, trio in enumerate(responses):
                call, isok, response = trio
                if not isok:
                    raise Exception("_createMultiple failed create()")
                # response is an rid
                rid = response
                rids.append(rid)
                pyonep.info(cik, rid, defer=True)

        # get info
        if pyonep.has_deferred(cik):
            responses = pyonep.send_deferred(cik)
            for i, trio in enumerate(responses):
                call, isok, response = trio
                if not isok:
                    raise Exception("_createMultiple failed info()")
                # response is info
                info = response
                resList[i].created(rids[i], info)
                res = resList[i]
                if res.alias is not None:
                    pyonep.map(cik, resList[i].rid, res.alias, defer=True)
                self.l("Created {}, rid: {}".format(res.type, res.rid))

        # map to aliases
        if pyonep.has_deferred(cik):
            responses = pyonep.send_deferred(cik)
            for i, trio in enumerate(responses):
                call, isok, response = trio
                if not isok:
                    raise Exception("_createMultiple failed map()")

    def _create(self, res):
        '''Creates a resource at the command line.'''
        alias = [] if res.alias is None else [res.alias]
        r = rpc('create',
                res.parentcik,
                '--type=' + res.type,
                '-',
                *alias,
                stdin=json.dumps(res.desc))
        self.assertTrue(r.exitcode == 0, 'create succeeds')

        rid = re.match('rid: ({})'.format(self.RE_RID), r.stdout).groups()[0]
        ri = rpc('info', res.parentcik, rid)
        info = json.loads(ri.stdout.strip())
        res.created(rid, info)

        # test that description contains what we asked for
        self.l('''Comparing keys.
Asked for desc: {}\ngot desc: {}'''.format(res.desc, res.info['description']))
        for k, v in res.desc.iteritems():
            if k != 'limits':
                self.l(k)
                self.assertTrue(
                    res.info['description'][k] == v,
                    'created resource matches spec')

        if res.type == 'client':
            m = re.match('^cik: ({})$'.format(self.RE_RID), r.stdout.split('\n')[1])
            self.l(r.stdout)
            self.assertTrue(m is not None)
            cik = m.groups()[0]
            self.assertTrue(res.info['key'] == cik)

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
        self._createMultiple(self.portalcik, [self.client])

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
                record=[[163299600, 'home brew'], [543212345, 'nonsense']],
                alias='string_port_alias'),
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

        self._createMultiple(self.client.cik(), self.resources)

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
        '''Write command'''
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
        '''Record command'''
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
        self.assertTrue(
            re.match("cik: {}.*".format(cik), r.stdout) is not None)
        # has correct number of lines
        self.assertTrue(len(r.stdout.split('\n')) == len(self.resources) + 1)

    def map_test(self):
        '''Map/unmap commands'''
        cik = self.client.cik()
        for res in self.resources:
            alias = 'foo'
            r = rpc('info', cik, alias)
            self.assertTrue(r.exitcode == 1, "info with alias should not work")
            r = rpc('map', cik, res.rid, alias)
            self.assertTrue(r.exitcode == 0, "map should work")
            r = rpc('info', cik, alias)
            self.assertTrue(r.exitcode == 0, "info with alias should work")
            r = rpc('unmap', cik, alias)
            self.assertTrue(r.exitcode == 0, "unmap should work")
            r = rpc('info', cik, alias)
            self.assertTrue(r.exitcode == 1, "info with alias should not work")
            r = rpc('unmap', cik, alias)
            self.assertTrue(r.exitcode == 0, "unmap with umapped alias should work")

    def create_test(self):
        '''Create command'''
        client = Resource(
            self.portalcik,
            'client',
            {'limits': {'dataport': 'inherit',
                        'datarule': 'inherit',
                        'dispatch': 'inherit',
                        'disk': 'inherit',
                        'io': 'inherit',
                        'share': 'inherit',
                        'client': 'inherit',
                        'sms': 'inherit',
                        'sms_bucket': 'inherit',
                        'email': 'inherit',
                        'email_bucket': 'inherit',
                        'http': 'inherit',
                        'http_bucket': 'inherit',
                        'xmpp': 'inherit',
                        'xmpp_bucket': 'inherit',
                        },
            "name": "test_create_client",
            "public": False})
        self._create(client)

        # test details for create, read, and write tests.
        resources = [
            Resource(
                client.cik(),
                'dataport',
                {'format': 'integer', 'name': 'int_port'},
                write=['-1', '0', '100000000'],
                record=[[665366400, '42']]),
            Resource(
                client.cik(),
                'dataport',
                {'format': 'boolean', 'name': 'boolean_port'},
                write=['false', 'true', 'false'],
                record=[[-100, 'true'], [-200, 'false'], [-300, 'true']]),
            Resource(
                client.cik(),
                'dataport',
                {'format': 'string', 'name': 'string_port'},
                write=['test', 'a' * 300],
                record=[[163299600, 'home brew'], [543212345, 'nonsense']]),
            Resource(
                client.cik(),
                'dataport',
                {'format': 'float', 'name': 'float_port'},
                write=['-0.1234567', '0', '3.5', '100000000.1'],
                record=[[-100, '-0.1234567'], [-200, '0'], [-300, '3.5'], [-400, '10000000.1']]),
                # TODO: handle scientific notation from OneP '-0.00001'
            Resource(
                client.cik(),
                'dataport',
                {'format': 'binary', 'name': 'binary_port'})]

        for res in resources:
            self._create(res)

    def spark_test(self):
        '''Spark chart command'''
        cik = self.client.cik()
        rid = self._rid(
            rpc('create', cik, '--type=dataport', '--format=integer', '--ridonly').stdout)
        rpc('record', cik, rid, '--interval={}'.format(240), *['--value={}'.format(x) for x in range(1, 6)])
        r = rpc('spark', cik, rid, '--days=1')
        m = re.match("[^ ] {59}\n4m", r.stdout)
        self.assertTrue(m is not None, "equally spaced points")
        rpc('flush', cik, rid)
        r = rpc('spark', cik, rid, '--days=1')
        self.assertTrue(r.exitcode == 0 and r.stdout == '', "no data should output nothing")
        r = rpc('record', cik, rid, '--value=-1,1', '--value=-62,2', '--value=-3662,3', '--value=-3723,4')
        self.assertTrue(r.exitcode == 0, "record points")
        r = rpc('spark', cik, rid, '--days=1')
        self.l(u'stdout: {} ({})'.format(r.stdout, len(r.stdout)))
        m = re.match("^[^ ] {58}[^ ]\n1m 1s +1h$", r.stdout)
        self.assertTrue(m is not None, "three points, two intervals")

    def _latest(self, cik, rid, val, msg):
        r = rpc('read', cik, rid, '--format=raw')
        self.l(r.stdout)
        self.assertTrue(r.stdout == val, msg)

    def script_test(self):
        '''Script upload'''
        waitsec = 8
        cik = self.client.cik()
        r = rpc('script', 'files/helloworld.lua', cik)
        self.assertTrue(r.exitcode == 0, 'New script')
        time.sleep(waitsec)
        self._latest(cik, 'helloworld.lua', 'line 1: Hello world!',
                     'debug output within {} sec'.format(waitsec))
        self._latest(cik, 'string_port_alias', 'Hello dataport!',
                     'dataport write from script within {} sec'.format(waitsec))
        r = rpc('script', 'files/helloworld2.lua', cik, '--name={}'.format('helloworld.lua'))
        self.assertTrue(r.exitcode == 0, 'Update existing script')
        time.sleep(waitsec)
        self._latest(cik, 'helloworld.lua', 'line 1: Hello world 2!',
                     'debug output within {} sec'.format(waitsec))
        self._latest(cik, 'string_port_alias', 'Hello dataport 2!',
                     'dataport write from script within {} sec'.format(waitsec))
