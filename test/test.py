# -*- coding: utf-8 -*-
"""Exoline test
   Tests exoline commands. Requires portalcik to be set in config.py.

Usage:
  test.py <portal-cik>
"""
import sys
import json
import re
import time
from datetime import datetime
import logging
from unittest import TestCase
import itertools
import os

from dateutil import parser

from exoline import exo
from exoline.exo import ExolineOnepV1
from exoline import timezone

try:
    from testconfig import config
except:
    sys.stderr.write(
        "Copy testconfig.py.template to testconfig.py and set portalcik.")


logging.basicConfig(stream=sys.stderr)
logging.getLogger("TestRPC").setLevel(logging.DEBUG)
logging.getLogger("run").setLevel(logging.DEBUG)
logging.getLogger("pyonep.onep").setLevel(logging.ERROR)
log = logging.getLogger("run")


def abbrev(s, length=1000):
    if len(s) > length:
        s = s[:length / 2] + '\n...\n' + s[-length / 2:]
    return s


def rpc(*args, **kwargs):
    stdin = kwargs.get('stdin', None)
    if True:
        argv = ['exo'] + list(args)
        log.debug(' '.join([str(a) for a in argv]))
        if stdin is not None:
            log.debug('    stdin: ' + abbrev(stdin))
    return exo.run(argv, stdin=stdin)


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

    def __str__(self):
        return 'Resource (parent {0}, type {1}, desc {2})'.format(self.parentcik, self.type, self.desc)

    def __repr__(self):
        return str(self)

    def created(self, rid, info):
        self.rid = rid
        self.info = info

    def cik(self):
        return self.info['key']


class TestRPC(TestCase):
    RE_RID = '[0-9a-f]{40}'

    def _logall(self, r):
        self.l(u'stdout: {0}\nstdout length:{1}\nstderr: {2}\nstderr length:{3}'.format(abbrev(r.stdout),
                                                                                        len(r.stdout),
                                                                                        abbrev(r.stderr),
                                                                                        len(r.stderr)))

    def _stdre(self, r, msg, search, match, stderr=False):
        std, label = (r.stderr, "stderr") if stderr else (r.stdout, "stdout")
        if search is not None:
            self.assertTrue(re.search(search, std, flags=re.MULTILINE) is not None,
                            msg + u' - failed to find in {1}:\n{2}\nsearch expression:\n{0}\nlengths: {3} (search) vs. {4} ({1})'.format(search, label, std, len(search), len(std)))
        if match is not None:
            self.assertTrue(re.match(match, std, flags=re.MULTILINE) is not None,
                            msg + u' - failed to match in {1}:\n{2}\nmatch expression:\n{0}\nlengths: {3} (match) vs. {4} ({1})'.format(match, label, std, len(match), len(std)))

    def notok(self, response, msg='', search=None, match=None):
        if response.exitcode == 0:
            self._logall(response)
        self.assertNotEqual(response.exitcode, 0, msg + ' (exit code should not be 0)')
        self._stdre(response, msg, search=search, match=match, stderr=True)

    def ok(self, response, msg='', search=None, match=None):
        if response.exitcode != 0:
            self._logall(response)
        self.assertEqual(response.exitcode, 0, msg + ' (exit code should be 0)')
        self._stdre(response, msg, search=search, match=match, stderr=False)

    def _rid(self, s):
        '''Parse rid from s, raising an exception if it doesn't validate.'''
        m = re.match("^({0}).*".format(self.RE_RID), s)
        self.assertFalse(m is None, "rid: {0}".format(s))
        return str(m.groups()[0])

    def _ridcik(self, s):
        '''Parse rid and cik from output of create command, and raise
        exception if it doesn't validate.'''
        m = re.match("^rid: ({0})\ncik: ({0})$".format(self.RE_RID),
                     s,
                     re.MULTILINE)
        self.l(s)
        return [str(g) for g in m.groups()]

    def _createMultiple(self, cik, resList):
        # use pyonep directly
        pyonep = exo.ExoRPC().exo
        for res in resList:
            pyonep.create(cik, res.type, res.desc, defer=True)

        rids = []
        # create resources
        responses = pyonep.send_deferred(cik)
        for i, trio in enumerate(responses):
            call, isok, response = trio
            self.l('{0}'.format(resList))
            self.assertTrue(isok, "create should succeed")
            # response is an rid
            rid = response
            rids.append(rid)
            pyonep.info(cik, rid, defer=True)

        # get info
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

        return rids

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
        ri = rpc('info', res.parentcik, rid, '--exclude=counts,usage')
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

    def _createDataports(self, cik=None):
        # test one of each type of dataport
        if cik is None:
            cik = self.client.cik()
        stdports = {}
        stdports['integer'] = Resource(
            cik, 'dataport', {'format': 'integer', 'name': 'int_port'},
            write=['-1', '0', '100000000'],
            record=[[665366400, '42']])
        stdports['boolean'] = Resource(
            cik, 'dataport', {'format': 'boolean', 'name': 'boolean_port'},
            write=['false', 'true', 'false'],
            record=[[-100, 'true'], [-200, 'false'], [-300, 'true']])
        stdports['string'] = Resource(
            cik, 'dataport', {'format': 'string', 'name': 'string_port'},
            alias='string_port_alias',
            write=['test', 'a' * 300],
            record=[[163299600, 'home brew'], [543212345, 'nonsense']])
        stdports['float'] = Resource(
            cik, 'dataport', {'format': 'float', 'name': 'float_port'},
            write=['-0.1234567', '0', '3.5', '100000000.1'],
            record=[[-100, '-0.1234567'], [-200, '0'], [-300, '3.5'], [-400, '10000000.1']])
            # TODO: handle scientific notation from OneP '-0.00001'
        # TODO: handle binary dataport

        self._createMultiple(cik, stdports.values())

        return stdports


    def setUp(self):
        '''Create some devices in the portal to test'''
        self.log = logging.getLogger('TestRPC')
        self.portalcik = config['portalcik']
        self.client = Resource(
            self.portalcik,
            'client',
            {'limits': {'client': 'inherit',
                        'dataport': 'inherit',
                        'datarule': 'inherit',
                        'dispatch': 'inherit',
                        'disk': 'inherit',
                        'io': 'inherit'},
            'writeinterval': 'inherit',
            'name': 'testclient',
            'visibility': 'parent'})
        self._createMultiple(self.portalcik, [self.client])

    def tearDown(self):
        '''Clean up any test client'''
        rpc('drop', self.portalcik, self.client.rid)

    def _readBack(self, res, limit):
        r = rpc('read',
                res.parentcik,
                res.rid,
                '--limit={0}'.format(limit),
                '--timeformat=unix')
        log.debug(r.stdout)
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
        stdports = self._createDataports()
        for res in stdports.values():
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
        stdports = self._createDataports()
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

        for r in stdports.values():
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

        r = rpc('create', cik, '--type=client', '--cikonly')
        self.ok(r, 'create child')
        childcik = r.stdout

        stdports = self._createDataports(childcik)

        r = rpc('tree', cik)
        # call did not fail
        self.ok(r, 'tree shouldn\'t fail')
        # starts with cik
        self.l(r.stdout)
        self.assertTrue(
            re.match(".* cik: {0}.*".format(cik), r.stdout) is not None)

        # has correct number of lines
        self.assertTrue(len(r.stdout.split('\n')) == len(stdports) + 1 + 1)

        r = rpc('tree', cik, '--level=0')
        self.ok(r, 'tree with --level=0 shouldn\'t fail')
        self.ok(r)
        self.assertTrue(len(r.stdout.split('\n')) == 1)

        r = rpc('tree', cik, '--level=1')
        self.ok(r, 'tree with --level=1 shouldn\'t fail')
        self.assertTrue(len(r.stdout.split('\n')) == 2)

        r = rpc('tree', cik, '--level=2')
        self.ok(r, 'tree with --level=2 shouldn\'t fail')
        self.assertTrue(len(r.stdout.split('\n')) == len(stdports) + 1 + 1)

    def map_test(self):
        '''Map/unmap commands'''
        stdports = self._createDataports()
        cik = self.client.cik()
        for res in stdports.values():
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
        self.ok(r, 'drop --all-children succeeded')
        r = rpc('listing', client.cik(), '--type=dataport', '--plain')
        self.ok(r, 'no dataports after drop --all-children', match='')
        r = rpc('drop', self.portalcik, client.rid)
        self.ok(r, 'drop client succeeded')
        r = rpc('info', self.portalcik, client.rid)
        self.notok(r, 'client gone after drop', match='.*restricted')

    def spark_test(self):
        '''Spark command'''
        cik = self.client.cik()
        rid = self._rid(
            rpc('create', cik, '--type=dataport', '--format=integer', '--ridonly').stdout)
        rpc('record', cik, rid, '--interval={0}'.format(240), *['--value={0}'.format(x) for x in range(1, 6)])
        r = rpc('spark', cik, rid, '--days=1')
        self.ok(r, "equally spaced points", match="[^ ] {59}\n4m")
        rpc('flush', cik, rid)
        r = rpc('spark', cik, rid, '--days=1')
        self.ok(r, "no data should output nothing", match="")
        r = rpc('record', cik, rid, '--value=-1,1', '--value=-62,2', '--value=-3662,3', '--value=-3723,4')
        self.ok(r, "record points")
        r = rpc('spark', cik, rid, '--days=1')
        self.ok(r, "three points, two intervals", match="^[^ ] {58}[^ ]\n1m 1s +1h$")

    def _latest(self, cik, rid, val, msg):
        r = rpc('read', cik, rid, '--format=raw')
        self.assertEqual(r.exitcode, 0, 'read succeeded')
        self.l("{0} vs {1}".format(r.stdout, val))
        self.assertEqual(r.stdout, val, msg)

    def script_test(self):
        '''Script upload'''
        waitsec = 12
        cik = self.client.cik()
        desc = json.dumps({'limits': {'client': 1,
                                      'dataport': 'inherit',
                                      'datarule': 'inherit',
                                      'dispatch': 'inherit',
                                      'disk': 'inherit',
                                      'io': 'inherit'},
            'writeinterval': 'inherit',
            'name': 'testclient',
            'visibility': 'parent'})
        r = rpc('create', cik, '--type=client', '--name=firstChild', '-', stdin=desc)
        self.ok(r, 'create child 1')
        childrid1, childcik1 = self._ridcik(r.stdout)
        r = rpc('create', cik, '--type=client', '--name=secondChild', '-', stdin=desc)
        self.ok(r, 'create child 2')
        childrid2, childcik2 = self._ridcik(r.stdout)
        r = rpc('create', childcik2, '--type=client', '--name=grandChild')
        self.ok(r, 'create grandchild')
        childrid3, childcik3 = self._ridcik(r.stdout)

        lua1 = {'name': 'helloworld.lua',
                'path': 'files/helloworld.lua',
                'out': 'line 1: Hello world!',
                'portoutput': 'Hello dataport!'}
        lua1['content'] = open(lua1['path']).read().strip()
        lua2 = {'name': 'helloworld2.lua',
                'path': 'files/helloworld2.lua',
                'out': 'line 1: Hello world!',
                'portoutput': 'Hello dataport 2!'}
        lua2['content'] = open(lua2['path']).read().strip()

        def readscript(cik, alias):
            r = rpc('info', cik, alias, '--include=description')
            self.l(r.exitcode)
            self.l(r.stdout)
            self.l(r.stderr)
            info = json.loads(r.stdout)
            return info['description']['rule']['script'].strip()

        r = rpc('script', lua1['path'], cik)
        r = rpc('read', cik, lua1['name'])
        self.notok(r, "Don't create script unless --create passed")
        r = rpc('script', lua1['path'], '--create', cik)
        self.ok(r, 'New script')
        self.assertEqual(readscript(cik, lua1['name']), lua1['content'])
        #self._latest(cik, lua1['name'], lua1['out'],
        #             'debug output within {0} sec'.format(waitsec))
        #self._latest(cik, 'string_port_alias', lua1['portoutput'],
        #             'dataport write from script within {0} sec'.format(waitsec))
        r = rpc('script', lua2['path'], cik, '--name=' + lua1['name'])
        self.ok(r, 'Update existing script')
        self.assertEqual(readscript(cik, lua1['name']), lua2['content'])
        #self._latest(cik, lua1['name'], lua2['out'],
        #             'debug output from updated script within {0} sec'.format(waitsec))
        #self._latest(cik, 'string_port_alias', lua2['portoutput'],
        #             'dataport write from updated script within {0} sec'.format(waitsec))

        # test --recursive
        r = rpc('read', childcik1, lua1['name'])
        self.notok(r, 'not recursive when --recursive is not passed')
        r = rpc('script', lua1['path'], '--create', childcik2)
        self.ok(r, 'create script in one child')
        r = rpc('script', lua1['path'], '--recursive', cik)
        self.ok(r, 'recursively write a script')
        self.assertEqual(readscript(cik, lua1['name']), lua1['content'])
        self.assertEqual(readscript(childcik2, lua1['name']), lua1['content'])
        r = rpc('read', childcik1, lua1['name'])
        self.notok(r, 'script should not be created when --create is not passed')
        r = rpc('script', lua2['path'], cik, '--name=' + lua1['name'], '--recursive', '--create')
        self.ok(r, 'recursive script update to helloworld2')
        self.assertEqual(readscript(cik, lua1['name']), lua2['content'])
        self.assertEqual(readscript(childcik1, lua1['name']), lua2['content'], "child1 updated")
        self.assertEqual(readscript(childcik2, lua1['name']), lua2['content'], "child2 updated")
        self.assertEqual(readscript(childcik3, lua1['name']), lua2['content'], "grandchild updated")


    def usage_test(self):
        '''Get resource usage'''
        # This test passes inconsistently due to time passing between calls to
        # usage. Mainly all it was testing was date parsing, though.
        #r = rpc('usage', self.client.cik(), '--start=10/1/2012', '--end=11/1/2013')
        #self.assertTrue(r.exitcode == 0, 'usage call succeeded')
        #s1 = r.stdout
        #r = rpc('usage', self.client.cik(), '--start=10/1/2012', '--end=1383282000')
        #self.assertTrue(r.exitcode == 0, 'usage call succeeded')
        #s2 = r.stdout
        #r = rpc('usage', self.client.cik(), '--start=1349067600', '--end=1383282000')
        #self.assertTrue(r.exitcode == 0, 'usage call succeeded')
        #s3 = r.stdout
        #self.l(s1)
        #self.l(s2)
        #self.l(s3)
        #self.assertTrue(s1 == s2 and s2 == s3, 'various date forms output matches')
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
        # note that this measures seconds that the dataport existed, so time
        # must pass for the value to go up.
        time.sleep(1)
        r = rpc('usage', self.client.cik(), '--start=10/1/2012T13:04:05', '--end=now')
        dp2 = parse_metric('dataport', r)
        self.l("dp1: {0} dp2: {1}".format(dp1, dp2))
        self.assertTrue(dp2 > dp1, 'adding dataport added to dataport metric')

    def readmultiple_test(self):
        '''Read multiple RIDs'''
        stdports = self._createDataports()
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
            r = rpc('record', cik, stdports[fmt].rid,
                *['--value={0},{1}'.format(t, v) for t, v in data])
            self.assertTrue(r.exitcode == 0)

        rec('string', strings)
        rec('integer', integers)
        rec('float', floats)

        rids = [stdports[fmt].rid for fmt in ['string', 'integer', 'float']]
        r = rpc('read', '--start=2013-07-20T3:00:08', '--end=2013-07-20T3:00:08', cik, *rids)
        def parse_ts(s):
            return parse_ts_tuple(parser.parse(s).timetuple())

        def parse_ts_tuple(t):
            return int(time.mktime(t))

        def tolocaltz(s):
            # parse string and translate to local timezone with offset
            # specified
            tz = timezone.localtz()
            local_time_without_offset = datetime.fromtimestamp(parse_ts(s))
            return str(tz.localize(local_time_without_offset))

        self.ok(r, 'two readings on one timestamp', match='{0},,3,0.3'.format(tolocaltz('2013-07-20 03:00:08')))

        r = rpc('read', '--start=2013-07-20T2:40:07', '--end=2013-07-20T2:40:09', cik, *rids)
        self.l(r.stdout)
        lines = r.stdout.splitlines()
        self.assertEqual(lines[0], '{0},,,0.1'.format(tolocaltz('2013-07-20 02:40:09')), 'three timestamps')
        self.assertEqual(lines[1], '{0},,1,'.format(tolocaltz('2013-07-20 02:40:08')), 'three timestamps')
        self.assertEqual(lines[2], '{0},a,,'.format(tolocaltz('2013-07-20 02:40:07')), 'three timestamps')

        r = rpc('read', '--start=2013-07-20T3:00:09', cik, *rids)
        self.ok(r, "no data read succeeds", match='')

        rids.reverse()
        r = rpc('read', '--start=2013-07-20T3:00:08', '--end=2013-07-20T3:00:08', cik, *rids)
        self.ok(r, 'rid order reversed')
        self.assertTrue(r.stdout == '{0},0.3,3,'.format(tolocaltz('2013-07-20 03:00:08')), 'rid order reversed')

        rids = [rid for rid in itertools.chain(*json.loads(rpc('listing', cik, '--type=dataport', '--type=datarule').stdout))]

        # this test could be better -- for now, just verify that the right
        # number of columns come out
        r = rpc('read', '--start=2013-07-20T3:00:08', '--end=2013-07-20T3:00:08', '--timeformat=unix', cik)
        self.ok(r, 'read all RIDs', match='timestamp,' + ','.join(['.*' for rid in rids]) + '\n[0-9]+' + ','.join(['.*' for rid in rids]))

    def copy_diff_test(self):
        '''Copy and diff commands'''
        stdports = self._createDataports()
        cik = self.client.cik()

        r = rpc('diff', cik, self.client.cik())
        if sys.version_info < (2, 7):
            self.notok(r, 'diff not supported with Python <2.7')
        else:
            self.ok(r, 'diff with itself, no differences', match='')

        r = rpc('copy', cik, self.portalcik, '--cikonly')
        self.ok(r, 'copy test client', match=self.RE_RID)
        copycik = r.stdout

        r = rpc('diff', cik, copycik, '--no-children')
        if sys.version_info < (2, 7):
            self.notok(r, 'diff not supported with Python <2.7')
        else:
            self.ok(r, '--no-children, no differences', match='')

        r = rpc('diff', copycik, self.client.cik(), '--no-children')
        if sys.version_info < (2, 7):
            self.notok(r, 'diff not supported with Python <2.7')
        else:
            self.ok(r, 'reverse cik, still no differences', match='')

        r = rpc('diff', copycik, cik)
        if sys.version_info < (2, 7):
            self.notok(r, 'diff not supported with Python <2.7')
        else:
            self.ok(r, 'diff with children should match', match='')

        newalias = 'newalias'
        r = rpc('map', cik, stdports['string'].rid, newalias)
        self.ok(r, 'add an alias')
        r = rpc('diff', copycik, cik)
        if sys.version_info < (2, 7):
            self.notok(r, 'diff not supported with Python <2.7')
        else:
            self.ok(r, 'diff notices new alias', search=r'^\+.*' + newalias)
        r = rpc('diff', cik, copycik)
        if sys.version_info < (2, 7):
            self.notok(r, 'diff not supported with Python <2.7')
        else:
            self.ok(r, 'diff notices new alias (reversed)', search=r'^\-.*' + newalias)

        r = rpc('lookup', copycik, 'string_port_alias')
        self.ok(r, 'lookup copy dataport')
        copyrid = r.stdout
        r = rpc('map', copycik, copyrid, newalias)
        self.ok(r, 'add same alias to copy')
        r = rpc('diff', cik, copycik)
        if sys.version_info < (2, 7):
            self.notok(r, 'diff not supported with Python <2.7')
        else:
            self.ok(r, 'aliases match now', match='')

        '''
        r = rpc('copy', cik, cik, '--cikonly')
        self.ok(r, 'copy client into itself', match=self.RE_RID)
        innercik = r.stdout

        r = rpc('copy', copycik, copycik, '--cikonly')
        self.ok(r, 'copy client copy into itself', match=self.RE_RID)
        innercopycik = r.stdout

        r = rpc('lookup', innercopycik, 'string_port_alias')
        self.ok(r, 'lookup dataport on inner cik copy', match=self.RE_RID)
        innercopydataportrid = r.stdout
        '''

    def _stddesc(self, name):
        return {'limits': {'client': 'inherit',
                        'dataport': 'inherit',
                        'datarule': 'inherit',
                        'dispatch': 'inherit',
                        'disk': 'inherit',
                        'io': 'inherit'},
            'writeinterval': 'inherit',
            'name': name,
            'visibility': 'parent'}

    def copy_comment_test(self):
        '''Copy comments'''
        cik = self.client.cik()

        desc = json.dumps({'limits': {'client': 1,
                                      'dataport': 'inherit',
                                      'datarule': 'inherit',
                                      'dispatch': 'inherit',
                                      'disk': 'inherit',
                                      'io': 'inherit'},
            'writeinterval': 'inherit',
            'name': 'testclient',
            'visibility': 'parent'})
        r = rpc('create', cik, '--type=client', '--name=child', '-', stdin=desc)
        self.ok(r, 'create child client')
        childrid, childcik = self._ridcik(r.stdout)

        ridFloat, ridString = self._createMultiple(childcik, [
            Resource(cik, 'dataport', {'format': 'float', 'name': 'float_port'}),
            Resource(cik, 'dataport', {'format': 'string', 'name': 'string_port'})])

        r = rpc('copy', childcik, cik, '--cikonly')
        self.ok(r, 'make copy without comments')
        copy_without_comments = r.stdout

        r = rpc('diff', childcik, copy_without_comments)
        if sys.version_info < (2, 7):
            self.notok(r, 'diff not supported with Python <2.7')
        else:
            self.ok(r, 'no differences', match='')

        # add comments
        exo = ExolineOnepV1()
        exo.comment(childcik, ridFloat, 'public', 'Hello')
        exo.comment(childcik, ridFloat, 'public', 'World')

        r = rpc('diff', childcik, copy_without_comments)
        if sys.version_info < (2, 7):
            self.notok(r, 'diff not supported with Python <2.7')
        else:
            self.ok(r, 'diff notices comment differences', search=r'^\+.+')

        r = rpc('copy', childcik, cik, '--cikonly')
        self.ok(r, 'make copy without comments')
        copy_with_comments = r.stdout

        r = rpc('diff', childcik, copy_with_comments)
        if sys.version_info < (2, 7):
            self.notok(r, 'diff not supported with Python <2.7')
        else:
            self.ok(r, 'no differences -- comment was copied', match='')


    def copy_limit_test(self):
        '''Check limits with copy command'''
        pass

    def connection_test(self):
        '''Connection settings'''
        cik = self.client.cik()

        r = rpc('--port=80', '--host=m2.exosite.com', '--http', 'info', cik)
        self.ok(r, 'valid port and host at command line')

        r = rpc('--https', 'info', cik)
        self.ok(r, 'https connection')

        r = rpc('--port=443', '--host=m2.exosite.com', 'info', cik)
        self.ok(r, 'invalid port')

        r = rpc('--port=88', 'info', cik)
        self.notok(r, 'wrong port', match='JSON RPC Request Exception.*')

    def info_test(self):
        '''Info command'''
        allkeys = ['aliases', 'basic', 'counts', 'description', 'key',
                   'shares', 'subscribers', 'tags', 'usage']
        cik = self.client.parentcik
        rid = self.client.rid

        # all keys at once
        r = rpc('info', cik, rid)
        self.ok(r, 'info on all keys')
        info = json.loads(r.stdout)
        for k in allkeys:
            self.assertTrue(k in info.keys(), 'found key {0} when options is empty'.format(k))

        for k in allkeys:
            # include each key
            r = rpc('info', cik, rid, '--include={0}'.format(k))
            self.ok(r, 'info --include={0}'.format(k))
            info = json.loads(r.stdout)
            self.assertTrue(info.keys() == [k], 'only requested key was returned')
            # exclude each key
            r = rpc('info', cik, rid, '--exclude={0}'.format(k))
            self.ok(r, 'info --exclude={0}'.format(k))
            info = json.loads(r.stdout)
            keys = info.keys()
            self.assertTrue(len(keys) == len(allkeys) - 1 and k not in keys)

    def read_test(self):
        '''Read command'''
        # record a large amount of data to a float datasource
        cik = self.client.cik()
        rid1, rid2 = self._createMultiple(cik, [
            Resource(cik, 'dataport', {'format': 'float', 'name': 'float_port'}),
            Resource(cik, 'dataport', {'format': 'string', 'name': 'string_port'})])

        numpts = 20000
        intervalsec = 60
        r = rpc('--httptimeout=480', 'record', cik, rid1,
                '--interval={0}'.format(intervalsec),
                '-', stdin='0.987654321\n' * numpts)
        self.ok(r, "create data")

        end = int(time.mktime(datetime.now().timetuple()))
        start = int(end - (numpts * intervalsec))
        self.l("{0},{1}".format(start, end))
        readcmd = ['--httptimeout=1', 'read', cik, rid1,
                   '--limit={0}'.format(numpts),
                   '--start={0}'.format(start),
                   '--end={0}'.format(end)]
        r = rpc(*readcmd)
        self.notok(r, "read a lot of data with a single big read")

        readcmdchunks = readcmd + ['--chunkhours=6']
        r = rpc(*readcmdchunks)
        self.ok(r, "read a lot of data with multiple reads")

        r = rpc('flush', cik, rid1)
        r = rpc('record', cik, rid1, '--value=41,12.33', '--value=42,12.34', '--value=43,12.35', '--value=-1,12.36')
        self.ok(r, 'record some points')
        r = rpc('read', cik, rid1, '--start=42', '--end=42', '--timeformat=unix', '--limit=3')
        self.ok(r, 'read window of 1 second', match='42,12.34')

        # TODO: why doesn't this match?
        #r = rpc('read', cik, rid1, '--start=42', '--end=43', '--timeformat=unix', '--limit=3')
        #self.ok(r, 'read window of 2 seconds', match='43,12.35\n42,12.34')

        r = rpc('read', cik, rid1, '--start=44', '--timeformat=unix', '--limit=2')
        self.ok(r, '--end has a default', match='[0-9]+,12.36')


    def sort_test(self):
        '''Read command with --sort flag'''
        cik = self.client.cik()
        rid = self._createMultiple(
            cik,
            [Resource(cik,
                      'dataport',
                      {'format': 'float', 'name': 'float_port'})])[0]

        r = rpc('write', cik, rid, '--value=1')
        self.ok(r, 'write 1')
        time.sleep(1)
        r = rpc('write', cik, rid, '--value=2')
        self.ok(r, 'write 2')
        time.sleep(1)
        r = rpc('write', cik, rid, '--value=3')
        self.ok(r, 'write 3')
        time.sleep(1)

        r = rpc('read', cik, rid, '--limit=2', '--format=raw', '--sort=asc')
        self.ok(r, 'read two points, ascending', match="1\n2")

        r = rpc('read', cik, rid, '--limit=2', '--format=raw', '--sort=desc')
        self.ok(r, 'read two points, descending', match="3\n2")

        r = rpc('read', cik, rid, '--limit=2', '--format=raw')
        self.ok(r, 'read two points, ascending (desc is default)', match="3\n2")

        r = rpc('read', cik, rid, '--limit=3', '--format=raw', '--sort=desc')
        self.ok(r, 'read two points, descending', match="3\n2\n1")

    def ip_test(self):
        '''ip command'''
        r = rpc('ip')
        self.ok(r, 'ip command succeeds', match='\d+,\d+,\d+,\d+,\d+,\d+')

    def data_test(self):
        '''Data command'''
        cik = self.client.cik()
        rid_float, rid_str, rid_integer = self._createMultiple(
            cik,
            [Resource(cik, 'dataport',
                      {'format': 'float'},
                      alias='float'),
             Resource(cik, 'dataport',
                      {'format': 'string'},
                      alias='string'),
             Resource(cik, 'dataport',
                      {'format': 'integer'},
                      alias='integer')])

        r = rpc('data', cik, '--read=float')
        self.ok(r, 'read dataport with no value', '')

        r = rpc('data', cik + 'a', '--write=float,3.1415')
        self.notok(r, 'bad cik fails')

        r = rpc('data', cik, '--write=float')
        self.notok(r, 'bad write format fails')

        r = rpc('data', cik, '--write=float,,2')
        self.notok(r, 'multiple commas in write fails')

        r = rpc('data', cik, '--write=float,3.1415')
        self.ok(r, 'write single value', match='')

        r = rpc('data', cik, '--read=float', '--read=integer')
        self.ok(r, 'read two values, only one of which exists', match='float=3.1415')

        r = rpc('data', cik, '--write=string,foo', '--write=integer,616')
        self.ok(r, 'write multiple values', match='')

        r = rpc('data', cik, '--read=string', '--read=integer', '--read=float')
        self.ok(r, 'read multiple values', match='float=3.1415&integer=616&string=foo')

        r = rpc('data', cik, '--read=integer', '--read=float', '--read=string')
        self.ok(r, 'read multiple values, different order', match='string=foo&float=3.1415&integer=616')

        r = rpc('data', cik, '--read=integer', '--write=float,17.5', '--write=string,bar', '--read=string')
        # TODO: why does the platform return string=foo&integer=616 sometimes?
        #self.ok(r, 'write and read multiple values', match='string=bar&integer=616')
        self.ok(r, 'write and read multiple values', search='string=[a-z]{3}&integer=616')

    def update_test(self):
        '''Update command'''
        cik = self.client.cik()

        rid = self._createMultiple(
            cik,
            [Resource(cik, 'dataport',
                      {'format': 'float', 'name': 'Original Name'},
                      alias='float')])[0]

        r = rpc('info', cik, rid, '--include=description')
        info_old = json.loads(r.stdout)
        name_old = info_old['description']['name']

        r = rpc('update', cik, rid, '-', stdin=json.dumps({'name': 'update_test'}))
        self.ok(r, 'update name', match='ok')

        r = rpc('info', cik, rid, '--include=description')
        info_new = json.loads(r.stdout)
        name_new = info_new['description']['name']

        log.debug(name_old)
        log.debug(name_new)
        log.debug('Description:')
        log.debug(json.dumps(info_old))
        log.debug(json.dumps(info_new))
        self.assertTrue(name_old != name_new, 'client name was changed')
        self.assertTrue(name_new == "update_test", 'new name is correct')

        info_new['description']['name'] = name_old
        self.assertTrue(info_old == info_new, 'client name was only difference')

    def spec_test(self):
        '''Spec command'''
        cik = self.client.cik()
        spec = 'files/spec.yaml'
        r = rpc('spec', cik, spec)
        self.notok(r, 'no ids specified')
        r = rpc('spec', cik, spec, '--ids=1,2')
        self.ok(r, 'specify ids, client doesn''t match', search='not found')
        r = rpc('spec', cik, spec, '--ids=1,2', '--create')
        self.ok(r, 'create dataports and scripts based on spec')
        r = rpc('spec', cik, spec, '--ids=1,2')
        self.ok(r, 'create dataports and scripts based on spec', match='')

        # test correct number of children of each type
        r = rpc('listing', cik, '--type=dataport', '--type=datarule')
        self.ok(r, 'get listing of client')
        dataports, datarules = json.loads(r.stdout)
        self.assertEqual(len(dataports), 5, 'created correct number of dataports')
        self.assertEqual(len(datarules), 3, 'created correct number of datarules')

        # test initial value
        r = rpc('read', cik, 'teststring_set1', '--format=raw')
        self.ok(r, 'check that initial value was created', match='my initial value')

        # test no initial value
        r = rpc('read', cik, 'teststring', '--format=raw')
        self.ok(r, 'check that no initial value was created', match='')

        # test format
        r = rpc('info', cik, 'teststring', '--include=description')
        self.ok(r, 'got info for teststring')
        description = json.loads(r.stdout)['description']
        self.assertEqual(description['format'], 'string', 'teststring is a string')

        # test format
        r = rpc('info', cik, 'testint_units', '--include=description')
        self.ok(r, 'got info for testint_units')
        description = json.loads(r.stdout)['description']
        self.assertEqual(description['format'], 'integer', 'testints_units is an integer')

        # test unit
        meta_string = description['meta']
        self.assertFalse(len(meta_string) == 0)
        meta = json.loads(meta_string)
        self.assertEqual(meta['datasource']['unit'], u'°F', 'unit set correctly based on spec')

        # test format content
        r = rpc('read', cik, 'testjson', '--format=raw')
        self.ok(r, 'read testjson initial value', match='{}')

        # TODO: test lua script templating
        # TODO: test that correct differences are reported. Change one thing
        # at a time, confirm report is correct, then confirm passing --create
        # resolves it.

        # text --example script
        r = rpc('drop', cik, '--all-children')
        self.ok(r, 'drop children from test client')
        r = rpc('spec', '--example')
        example_spec = 'files/tmp_examplespec.yaml'
        with open(example_spec, 'w') as f:
            print(r.stdout)
            f.write(r.stdout)
        r = rpc('spec', cik, example_spec, '--ids=A,B')
        self.ok(r, 'empty client does not match example spec', match='.+')
        r = rpc('spec', cik, example_spec, '--create', '--ids=A,B')
        self.ok(r, 'create from example spec')
        r = rpc('spec', cik, example_spec, '--ids=A,B')
        self.ok(r, 'client now matches example spec', match='')

        os.remove(example_spec)
