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
logging.getLogger("pyonep.onep").setLevel(logging.ERROR)
log = logging.getLogger("_cmd")


def _cmd(argv, stdin):
    '''Runs an exoline command, translating stdin from
    string and stdout to string. Returns a CmdResult.'''
    if True:
        log.debug(' '.join([str(a) for a in argv]))
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
        log.debug("Exit code was {0}".format(exitcode))
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
        m = re.match("^({0}).*".format(self.RE_RID), s)
        self.assertFalse(m is None, "rid: {0}".format(s))
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
                self.l("Created {0}, rid: {1}".format(res.type, res.rid))

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
        self.l(r.stdout)
        self.assertEqual(r.exitcode, 0, 'create succeeds')

        rid = re.match('rid: ({0})'.format(self.RE_RID), r.stdout).groups()[0]
        ri = rpc('info', res.parentcik, rid)
        info = json.loads(ri.stdout.strip())
        res.created(rid, info)

        # test that description contains what we asked for
        self.l('''Comparing keys.
Asked for desc: {0}\ngot desc: {1}'''.format(res.desc, res.info['description']))
        for k, v in res.desc.iteritems():
            if k != 'limits':
                self.l(k)
                self.assertTrue(
                    res.info['description'][k] == v,
                    'created resource matches spec')

        if res.type == 'client':
            m = re.match('^cik: ({0})$'.format(self.RE_RID), r.stdout.split('\n')[1])
            self.l(r.stdout)
            self.assertTrue(m is not None)
            cik = m.groups()[0]
            self.assertTrue(res.info['key'] == cik)

        self.l("Created {0}, rid: {1}".format(res.type, res.rid))
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
        cik = self.client.cik()
        self.dataports = {}
        self.dataports['integer'] = Resource(
            cik, 'dataport', {'format': 'integer', 'name': 'int_port'},
            write=['-1', '0', '100000000'],
            record=[[665366400, '42']])
        self.dataports['boolean'] = Resource(
            cik, 'dataport', {'format': 'boolean', 'name': 'boolean_port'},
            write=['false', 'true', 'false'],
            record=[[-100, 'true'], [-200, 'false'], [-300, 'true']])
        self.dataports['string'] = Resource(
            cik, 'dataport', {'format': 'string', 'name': 'string_port'},
            alias='string_port_alias',
            write=['test', 'a' * 300],
            record=[[163299600, 'home brew'], [543212345, 'nonsense']])
        self.dataports['float'] = Resource(
            cik, 'dataport', {'format': 'float', 'name': 'float_port'},
            write=['-0.1234567', '0', '3.5', '100000000.1'],
            record=[[-100, '-0.1234567'], [-200, '0'], [-300, '3.5'], [-400, '10000000.1']])
            # TODO: handle scientific notation from OneP '-0.00001'
        # TODO: handle binary dataport

        self.resources = self.dataports.values()

        self._createMultiple(cik, self.resources)

    def tearDown(self):
        '''Clean up any test client'''
        rpc('drop', self.portalcik, self.client.rid)

    def _readBack(self, res, limit):
        r = rpc('read',
                res.parentcik,
                res.rid,
                '--limit={0}'.format(limit),
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
        self.l('Wrote {0}'.format(wrotevalues))
        self.l('Read  {0}'.format(readvalues))
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
        self.l('Wrote     {0}'.format(wrotevalues))
        self.l('wv_errors {0}'.format(wv_errors))
        self.l('Read      {0}'.format(readvalues))
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
                        '--value={0},{1}'.format(timestamp, value))
                self.assertTrue(r.exitcode == 0)
                time.sleep(1)

        def one_line(res):
            r = rpc('record',
                    res.parentcik,
                    res.rid,
                    *['--value={0},{1}'.format(t, v) for t, v in res.record])
            self.assertTrue(r.exitcode == 0)

        def on_stdin(res):
            r = rpc('record',
                    res.parentcik,
                    res.rid,
                    '-',
                    stdin='\n'.join(['{0},{1}'.format(t, v) for t, v in res.record]))
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
            re.match("cik: {0}.*".format(cik), r.stdout) is not None)
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
        '''Create/drop commands'''
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

        # set up a few standard dataports
        cik = client.cik()
        dataports = {}
        resources = [
            Resource(cik, 'dataport', {'format': 'integer', 'name': 'int_port'}),
            Resource(cik, 'dataport', {'format': 'boolean', 'name': 'boolean_port'}),
            Resource(cik, 'dataport', {'format': 'string', 'name': 'string_port'}),
            Resource(cik, 'dataport', {'format': 'float', 'name': 'float_port'}),
        ]
        for res in resources:
            self._create(res)

        r = rpc('listing', client.cik(), '--type=dataport', '--plain')

        lines = r.stdout.split()
        lines.sort()
        rids = [r.rid for r in resources]
        rids.sort()
        self.l("{0} {1}".format(lines, rids))
        self.assertTrue(lines == rids, 'listing after create')
        r = rpc('drop', client.cik(), '--all-children')
        self.assertEqual(r.exitcode, 0, 'drop --all-children succeeded')
        r = rpc('listing', client.cik(), '--type=dataport', '--plain')
        self.assertTrue(len(r.stdout) == 0), 'no dataports after drop --all-children'
        r = rpc('drop', self.portalcik, client.rid)
        self.assertEqual(r.exitcode, 0, 'drop client succeeded')
        r = rpc('info', self.portalcik, client.rid)
        self.assertTrue(r.exitcode != 0 and r.stderr.endswith('restricted'), 'client gone after drop')


    def spark_test(self):
        '''Intervals command'''
        cik = self.client.cik()
        rid = self._rid(
            rpc('create', cik, '--type=dataport', '--format=integer', '--ridonly').stdout)
        rpc('record', cik, rid, '--interval={0}'.format(240), *['--value={0}'.format(x) for x in range(1, 6)])
        r = rpc('intervals', cik, rid, '--days=1')
        m = re.match("[^ ] {59}\n4m", r.stdout)
        self.assertTrue(m is not None, "equally spaced points")
        rpc('flush', cik, rid)
        r = rpc('intervals', cik, rid, '--days=1')
        self.assertTrue(r.exitcode == 0 and r.stdout == '', "no data should output nothing")
        r = rpc('record', cik, rid, '--value=-1,1', '--value=-62,2', '--value=-3662,3', '--value=-3723,4')
        self.assertTrue(r.exitcode == 0, "record points")
        r = rpc('intervals', cik, rid, '--days=1')
        self.l(u'stdout: {0} ({1})'.format(r.stdout, len(r.stdout)))
        m = re.match("^[^ ] {58}[^ ]\n1m 1s +1h$", r.stdout)
        self.assertTrue(m is not None, "three points, two intervals")

    def _latest(self, cik, rid, val, msg):
        r = rpc('read', cik, rid, '--format=raw')
        self.assertEqual(r.exitcode, 0, 'read succeeded')
        self.l("{0} vs {1}".format(r.stdout, val))
        self.assertEqual(r.stdout, val, msg)

    def script_test(self):
        '''Script upload'''
        waitsec = 12
        cik = self.client.cik()
        r = rpc('script', 'files/helloworld.lua', cik)
        self.assertTrue(r.exitcode == 0, 'New script')
        time.sleep(waitsec)
        self._latest(cik, 'helloworld.lua', 'line 1: Hello world!',
                     'debug output within {0} sec'.format(waitsec))
        self._latest(cik, 'string_port_alias', 'Hello dataport!',
                     'dataport write from script within {0} sec'.format(waitsec))
        r = rpc('script', 'files/helloworld2.lua', cik, '--name={0}'.format('helloworld.lua'))
        self.assertTrue(r.exitcode == 0, 'Update existing script')
        time.sleep(waitsec)
        self._latest(cik, 'helloworld.lua', 'line 1: Hello world 2!',
                     'debug output from updated script within {0} sec'.format(waitsec))
        self._latest(cik, 'string_port_alias', 'Hello dataport 2!',
                     'dataport write from updated script within {0} sec'.format(waitsec))

    def usage_test(self):
        '''OneP resource usage'''
        r = rpc('usage', self.client.cik(), '--start=10/1/2012', '--end=11/1/2013')
        self.assertTrue(r.exitcode == 0, 'usage call succeeded')
        s1 = r.stdout
        r = rpc('usage', self.client.cik(), '--start=10/1/2012', '--end=1383282000')
        self.assertTrue(r.exitcode == 0, 'usage call succeeded')
        s2 = r.stdout
        r = rpc('usage', self.client.cik(), '--start=1349067600', '--end=1383282000')
        self.assertTrue(r.exitcode == 0, 'usage call succeeded')
        s3 = r.stdout
        self.l(s1)
        self.l(s2)
        self.l(s3)
        self.assertTrue(s1 == s2 and s2 == s3, 'various date forms output matches')
        def parse_metric(metric, r):
            self.assertTrue(r.exitcode == 0, 'usage call succeeded')
            self.l(r.stdout)
            m = re.match(".*{0}: (\d+).*".format(metric), r.stdout, re.DOTALL)
            self.assertTrue(m is not None, 'match metric {0} in results'.format(metric))
            return int(m.groups()[0])
        r = rpc('usage', self.client.cik(), '--start=10/1/2012T13:04:05')
        dp1 = parse_metric('dataport', r)
        self._create(Resource(self.client.cik(),
                              'dataport',
                              {'format': 'integer', 'name': 'int_port'}))
        r = rpc('usage', self.client.cik(), '--start=10/1/2012T13:04:05', '--end=now')
        dp2 = parse_metric('dataport', r)
        self.l("dp1: {0} dp2: {1}".format(dp1, dp2))
        # TODO: why does this not increase consistently?
        self.assertTrue(dp2 > dp1, 'adding dataport added to dataport metric')

    def readmultiple_test(self):
        '''Read multiple RIDs'''
        dataports = []
        strings =  [('2013-07-20T02:40:07', 'a'),
                    ('2013-07-20T02:50:07', 'b'),
                    ('2013-07-20T03:00:07', 'c')]
        integers = [('2013-07-20T02:40:08', 1),
                    ('2013-07-20T02:50:07', 2),
                    ('2013-07-20T03:00:08', 3)]
        floats =   [('2013-07-20T02:40:09', 0.1),
                    ('2013-07-20T02:50:09', 0.2),
                    ('2013-07-20T03:00:08', 0.3)]
        cik = self.client.cik()
        def rec(fmt, data):
            r = rpc('record', cik, self.dataports[fmt].rid,
                *['--value={0},{1}'.format(t, v) for t, v in data])
            self.assertTrue(r.exitcode == 0)

        rec('string', strings)
        rec('integer', integers)
        rec('float', floats)

        rids = [self.dataports[fmt].rid for fmt in ['string', 'integer', 'float']]
        r = rpc('read', '--start=2013-07-20T3:00:08', '--end=2013-07-20T3:00:08', cik, *rids)
        self.assertEqual(r.exitcode, 0, 'read with multiple rids')
        self.assertTrue(r.stdout == '2013-07-20 03:00:08,,3,0.3', 'two readings on one timestamp')

        r = rpc('read', '--start=2013-07-20T2:40:07', '--end=2013-07-20T2:40:09', cik, *rids)
        self.l(r.stdout)
        lines = r.stdout.splitlines()
        self.assertEqual(lines[0], '2013-07-20 02:40:09,,,0.1', 'three timestamps')
        self.assertEqual(lines[1], '2013-07-20 02:40:08,,1,', 'three timestamps')
        self.assertEqual(lines[2], '2013-07-20 02:40:07,a,,', 'three timestamps')

        r = rpc('read', '--start=2013-07-20T3:00:09', cik, *rids)
        self.assertEqual(r.exitcode, 0, 'no data read succeeds')
        self.assertTrue(r.stdout == '', 'no data')

        rids.reverse()
        r = rpc('read', '--start=2013-07-20T3:00:08', '--end=2013-07-20T3:00:08', cik, *rids)
        self.assertTrue(r.stdout == '2013-07-20 03:00:08,0.3,3,', 'rid order reversed')

    def ok(self, response, msg=None):
        self.assertEqual(response.exitcode, 0, msg)

    def notok(self, response, msg=None):
        self.assertNotEqual(response.exitcode, 1, msg)

    def copy_test(self):
        '''Test copy and diff commands'''

        cik = self.client.cik()

        r = rpc('diff', cik, self.client.cik())
        self.assertEqual(r.exitcode, 0, 'diff with itself')
        self.assertTrue(len(r.stdout) == 0, 'diff with itself')

        r = rpc('copy', cik, self.portalcik, '--cikonly')
        self.assertEqual(r.exitcode, 0, 'copy test client')
        copycik = r.stdout

        r = rpc('diff', cik, copycik, '--no-children')
        self.assertEqual(r.exitcode, 0, 'diff no children call succeeds')
        self.assertTrue(len(r.stdout) == 0, 'diff client copy, no children no differences')

        #r = rpc('diff', copycik, self.client.cik(), '--no-children')
        #self.assertEqual(r.exitcode, 0, 'reverse cik order')
        #self.assertTrue(len(r.stdout) == 0, 'reverse cik order')

        r = rpc('diff', copycik, cik)
        self.l(r.stdout)
        self.assertEqual(r.exitcode, 0, 'diff with children call succeeds')
        self.assertTrue(len(r.stdout) == 0, 'diff with children matches')

        # add an alias
        r = rpc('map', cik, self.dataports['string'].rid, 'foo')
        self.ok(r, 'add alias')
        r = rpc('diff', copycik, cik)
        self.ok(r, 'diff with new alias')
        self.l(r.stdout)
        self.assertTrue(len(r.stdout) > 0, 'single alias difference')

        r = rpc('lookup', copycik, 'string_port_alias')
        self.ok(r, 'lookup copy dataport')
        copyrid = r.stdout
        r = rpc('map', copycik, copyrid, 'foo')
        self.ok(r, 'add same alias to copy')
        r = rpc('diff', cik, copycik)
        self.ok(r, 'diff with same alias')
        self.l(r.stdout)
        self.assertTrue(len(r.stdout) == 0, 'aliases match now')

