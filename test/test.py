# -*- coding: utf-8 -*-
"""Exoline test
   Tests exoline commands. Requires portalcik to be set in config.py.

Usage:
  test.py <portal-cik>
"""
from __future__ import unicode_literals

import sys
import json
import re
import time
from datetime import datetime
import logging
from unittest import TestCase
import itertools
import os
import random
import string
import filecmp
import tempfile
import zipfile

import six
import yaml
from six import iteritems
from dateutil import parser
from nose.plugins.attrib import attr
from tzlocal import get_localzone

from exoline import exo
from exoline.exo import ExolineOnepV1
from pyonep import provision

basedir = 'test'

try:
    from .testconfig import config
    if 'host' not in config:
        config['host'] = 'm2.exosite.com'
    if 'https' not in config:
        config['https'] = True
    if 'port' not in config:
        config['port'] = 443 if config['https'] else 80
except Exception as ex:
    print(ex)
    sys.stderr.write(
        "Copy testconfig.py.template to testconfig.py and set portalcik.")

logging.basicConfig(stream=sys.stderr)
logging.getLogger("TestRPC").setLevel(logging.DEBUG)
logging.getLogger("run").setLevel(logging.DEBUG)
logging.getLogger("pyonep.onep").setLevel(logging.ERROR)
log = logging.getLogger("run")

pop = provision.Provision(host=config['host'],
                          manage_by_cik=False,
                          port=config['port'],
                          verbose=True,
                          https=config['https'],
                          raise_api_exceptions=True)

def abbrev(s, length=1000):
    if len(s) > length:
        s = s[:length // 2] + '\n...\n' + s[-length // 2:]
    return s

def argmatch(args, pattern):
    for a in args:
        if re.match(pattern, a):
            return True
    return False

def rpc(*args, **kwargs):
    stdin = kwargs.get('stdin', None)
    # override configuration file
    noconfig = kwargs.get('noconfig', None)

    if noconfig or argmatch(args, '--http.*') or argmatch(args, '--port.*') or argmatch(args, '--host.*'):
        argv = ['exo']
    else:
        argv = ['exo', '--host', config['host'], '--port', config['port']]
        if not config['https']:
            argv.append('--http')
    argv = argv + list(args)
    if sys.version_info < (3, 0):
        log.debug(' '.join([unicode(a) for a in argv]))
    else:
        log.debug(' '.join([str(a) for a in argv]))

    if stdin is not None:
        log.debug('    stdin: ' + abbrev(stdin))
    return exo.run(argv, stdin=stdin)

def prv(*args):
    '''wrapper for provision calls'''
    return rpc('--vendortoken=' + config['vendortoken'], '--vendor=' + config['vendor'], *args)

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
        if self.type == 'client' and 'limits' not in self.desc:
            self.desc['limits'] = {
                'dataport': 'inherit',
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
                'xmpp_bucket': 'inherit'}

    def __str__(self):
        return 'Resource (parent {0}, type {1}, desc {2})'.format(self.parentcik, self.type, self.desc)

    def __repr__(self):
        return str(self)

    def created(self, rid, info):
        self.rid = rid
        self.info = info

    def cik(self):
        return self.info['key']


def makeRPC():
    return exo.ExoRPC(host=config['host'], https=config['https'], port=config['port'])

class TestRPC(TestCase):
    #def shortDescription(self):
    #    # show test function names rather than docstring
    #    return None

    RE_RID = '[0-9a-f]{40}'

    def _logall(self, r):
        self.l('stdout: {0}\nstdout length:{1}\nstderr: {2}\nstderr length:{3}'.format(abbrev(r.stdout),
                                                                                       len(r.stdout),
                                                                                       abbrev(r.stderr),
                                                                                       len(r.stderr)))

    def _stdre(self, r, msg, search, match, stderr=False):
        std, label = (r.stderr, "stderr") if stderr else (r.stdout, "stdout")
        if search is not None:
            self.assertTrue(
                re.search(search, std, flags=re.MULTILINE) is not None,
                msg + ' - failed to find in {1}:\n{2}\nsearch expression:\n{0}\nlengths: {3} (search) vs. {4} ({1})'.format(
                    search, label, std, len(search), len(std)))
        if match is not None:
            self.assertTrue(re.match(match, std, flags=re.MULTILINE) is not None,
                msg + ' - failed to match in {1}:\n{2}\nmatch expression:\n{0}\nlengths: {3} (match) vs. {4} ({1})'.format(
                    match, label, std, len(match), len(std)))

    def notok(self, response, msg='', search=None, match=None):
        self.assertTrue(
            type(response.exitcode) is int,
            'exit code is an int (found {0})'.format(type(response.exitcode)))
        if response.exitcode == 0:
            self._logall(response)
        self.assertNotEqual(response.exitcode, 0, msg + ' (exit code should not be 0)')
        self._stdre(response, msg, search=search, match=match, stderr=True)

    def ok(self, response, msg='', search=None, match=None):
        self.assertTrue(
            type(response.exitcode) is int,
            'exit code is an int (found {0})'.format(type(response.exitcode)))
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
        return [str(g) for g in m.groups()]

    def _createMultiple(self, cik, resList):
        # use pyonep directly
        pyonep = makeRPC().exo
        for res in resList:
            pyonep.create(cik, res.type, res.desc, defer=True)

        rids = []
        # create resources
        responses = pyonep.send_deferred(cik)
        for i, trio in enumerate(responses):
            call, isok, response = trio
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
        self.assertEqual(r.exitcode, 0, 'create succeeds')

        rid = re.match('rid: ({0})'.format(self.RE_RID), r.stdout).groups()[0]
        ri = rpc('info', res.parentcik, rid, '--exclude=counts,usage')
        info = json.loads(ri.stdout.strip())
        res.created(rid, info)

        # test that description contains what we asked for
        self.l('''Comparing keys.
Asked for desc: {0}\ngot desc: {1}'''.format(res.desc, res.info['description']))
        for k, v in iteritems(res.desc):
            if k != 'limits':
                self.assertTrue(
                    res.info['description'][k] == v,
                    'created resource matches spec')

        if res.type == 'client':
            m = re.match('^cik: ({0})$'.format(self.RE_RID), r.stdout.split('\n')[1])
            self.assertTrue(m is not None)
            cik = m.groups()[0]
            self.assertTrue(res.info['key'] == cik)

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
            write=['-1', '42'],
            record=[[665366400, '42']])
        stdports['string'] = Resource(
            cik, 'dataport', {'format': 'string', 'name': 'string_port_你好'},
            alias='string_port_alias',
            write=['hello', '你好'],
            record=[[163299600, 'hello'], [10, '你好']])
        stdports['float'] = Resource(
            cik, 'dataport', {'format': 'float', 'name': 'float_port'},
            write=['-0.1234567', '0', '3.5'],
            record=[[-100, '-0.1234567'], [-200, '0']])
            # TODO: handle scientific notation from OneP '-0.00001'

        self._createMultiple(cik, list(stdports.values()))

        return stdports


    def setUp(self):
        '''Create some devices in the portal to test'''
        self.log = logging.getLogger('TestRPC')
        self.portalcik = config['portalcik']
        self.client = Resource(
            self.portalcik,
            'client',
            {'writeinterval': 'inherit',
            'name': 'test測試',
            'visibility': 'parent'})
        self._createMultiple(self.portalcik, [self.client])

    def tearDown(self):
        '''Clean up any test client'''
        rpc('drop', self.portalcik, self.client.rid)

    @attr('auth')
    def auth_cik_clientid_test(self):
        '''Test using the <CIK:cRID> auth format'''
        cik = self.client.parentcik
        rid = self.client.rid

        auth = '{0}:c{1}'.format(cik, rid)
        isok = rpc('info', auth)
        self.ok(isok, 'info with <CIK:cRID>')

    @attr('auth')
    def auth_cik_resourceid_test(self):
        '''Test using the <CIK:rRID> auth format'''
        cik = self.client.parentcik
        rid = self._createDataports()

        auth = '{0}:r{1}'.format(cik, rid['string'].rid)
        isok = rpc('info', auth)
        self.ok(isok, 'info with <CIK:rRID>')

    @attr('auth')
    def auth_shortcut_clientid_test(self):
        '''Test using the <SHORTCUT:cRID> auth format'''
        cik = self.client.parentcik
        rid = self.client.rid

        with tempfile.NamedTemporaryFile('w+') as cfgfile:
            cfgfile.write("keys:\n")
            cfgfile.write("    testme: {0}".format(cik))
            cfgfile.flush()
            cfgs = "--config={0}".format(cfgfile.name)
            auth = 'testme:c{0}'.format(rid)
            isok = rpc(cfgs, 'info', auth)
            self.ok(isok, 'info with <SHORTCUT:cRID>')

    @attr('auth')
    def auth_shortcut_test(self):
        '''Test using the <SHORTCUT> auth format'''
        cik = self.client.parentcik
        rid = self.client.rid
        shortcut = '{0}:c{1}'.format(cik, rid)

        with tempfile.NamedTemporaryFile('w+') as cfgfile:
            cfgfile.write("keys:\n")
            cfgfile.write("    testme: {0}".format(shortcut))
            cfgfile.flush()
            cfgs = "--config={0}".format(cfgfile.name)
            auth = 'testme'
            isok = rpc(cfgs, 'info', auth)
            self.ok(isok, 'info with <SHORTCUT>')


    def _readBack(self, res, limit):
        r = rpc('read',
                res.parentcik,
                res.rid,
                '--limit={0}'.format(limit),
                '--timeformat=unix')
        if sys.version_info < (3, 0):
            r.stdout = r.stdout.decode('utf-8')
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

        # it seems as though if you pass '0' the platform reads '0.0', and vice
        # versa.
        wrote = ['0' if x == '0.0' else x for x in wrotevalues]
        read = ['0' if x == '0.0' else x for x in readvalues_notime]
        self.assertTrue(wrote == read,
                        'Read values did not match written values. Expected {0}, got {1}.'.format(
                            wrote,
                            read))

    def write_test(self):
        '''Write command'''
        stdports = self._createDataports()
        for res in list(stdports.values()):
            if res.type == 'dataport' and res.write is not None:
                # test writing
                if res.write is not None:
                    cik = res.parentcik
                    rid = res.rid

                    # test passing value on the command line
                    for value in res.write:
                        rpc('write', cik, rid, '--value=' + value)
                        # sleep for a second to prevent writing over the top of
                        # the previous value
                        time.sleep(1)
                    readvalues = self._readBack(res, len(res.write))
                    self._verifyWrite(res.write, readvalues)

                    # test the form of write that takes value from stdin
                    for value in res.write:
                        rpc('write', cik, rid, '-', stdin=value)
                        # sleep for a second to prevent writing over the top of
                        # the previous value
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
            stdin='\n'.join(['{0},{1}'.format(t, v) for t, v in res.record])
            r = rpc('record',
                    res.parentcik,
                    res.rid,
                    '-',
                    stdin=stdin)
            self.assertTrue(r.exitcode == 0)

        for r in list(stdports.values()):
            if r.type == 'dataport':
                _recordAndVerify(r, one_by_one)
                _flush(r)
                _recordAndVerify(r, one_line)
                _flush(r)
                _recordAndVerify(r, on_stdin)
                _flush(r)

    def run_tree_tsts(self, treecmd='tree', options=[]):
        cik = self.client.cik()

        r = rpc('drop', cik, '--all-children')

        r = rpc('create', cik, '--type=client', '--name=你好', '--cikonly')
        self.ok(r, 'create child')
        childcik = r.stdout

        stdports = self._createDataports(childcik)

        r = rpc(treecmd, cik, *options)
        # call did not fail
        self.ok(r, treecmd + ' shouldn\'t fail')
        # starts with cik
        self.assertTrue(
            re.match('.* cik: {0}.*'.format(cik), r.stdout) is not None)

        delim = '\n'.encode('utf-8')
        def get_lines(stdout):
            # has correct number of lines
            if sys.version_info < (3, 0):
                so = stdout
            else:
                so = stdout.encode('utf-8')
            return so.split(delim)

        self.assertTrue(len(get_lines(r.stdout)) == len(stdports) + 1 + 1)

        r = rpc(treecmd, cik, '--level=0', *options)
        self.ok(r, treecmd + ' with --level=0 shouldn\'t fail')
        self.assertTrue(len(get_lines(r.stdout)) == 1)

        r = rpc(treecmd, cik, '--level=1', *options)
        self.ok(r, treecmd + ' with --level=1 shouldn\'t fail')
        self.assertTrue(len(get_lines(r.stdout)) == 2)

        r = rpc(treecmd, cik, '--level=2', *options)
        self.ok(r, treecmd + ' with --level=2 shouldn\'t fail')
        self.assertTrue(len(get_lines(r.stdout)) == len(stdports) + 1 + 1)

        if treecmd != 'twee':
            r = rpc(treecmd, cik, '--values', *options)
            self.ok(r, treecmd + ' with --values shouldn\'t fail')

            r = rpc(treecmd, cik, '--verbose', *options)
            self.ok(r, treecmd + ' with --verbose shouldn\'t fail')
        else:
            r = rpc(treecmd, cik, '--rids', *options)
            self.ok(r, treecmd + ' with --rids should\'t fail')
            self.assertTrue(
                re.search('(cik:|rid\.)', r.stdout) is None,
                'look for things that shouldn\'t be in --rids output')

    def tree_test(self):
        '''Tree command'''
        self.run_tree_tsts('tree')

    def twee_test(self):
        '''Twee command'''
        self.run_tree_tsts('twee', ['--nocolor'])

    def map_test(self):
        '''Map/unmap commands'''
        stdports = self._createDataports()
        cik = self.client.cik()
        for res in list(stdports.values()):
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
            "name": "test_你好",
            "public": False})
        self._create(client)

        # set up a few standard dataports
        cik = client.cik()
        dataports = {}
        resources = [
            Resource(cik, 'dataport', {'format': 'integer', 'name': 'int_port_你好'}),
            Resource(cik, 'dataport', {'format': 'string', 'name': 'string_port_你好'}),
            Resource(cik, 'dataport', {'format': 'float', 'name': 'float_port_你好'}),
        ]
        for res in resources:
            self._create(res)

        r = rpc('listing', client.cik(), '--types=dataport', '--plain')

        lines = r.stdout.split()
        lines.sort()
        rids = [r.rid for r in resources]
        rids.sort()
        self.l("{0} {1}".format(lines, rids))
        self.assertTrue(lines == rids, 'listing after create')
        r = rpc('drop', client.cik(), '--all-children')
        self.ok(r, 'drop --all-children succeeded')
        r = rpc('listing', client.cik(), '--types=dataport', '--plain')
        self.ok(r, 'no dataports after drop --all-children', match='')
        r = rpc('drop', self.portalcik, client.rid)
        self.ok(r, 'drop client succeeded')
        r = rpc('info', self.portalcik, client.rid)
        self.notok(r, 'client gone after drop', match='.*restricted')

    #these fail occasionally due to some timing thing. Need to figure out why.
    #def spark_test(self):
    #    '''Spark command'''
    #    cik = self.client.cik()
    #    rid = self._rid(
    #        rpc('create', cik, '--type=dataport', '--format=integer', '--ridonly').stdout)
    #    rpc('record', cik, rid, '--interval={0}'.format(240), *['--value={0}'.format(x) for x in range(1, 6)])
    #    r = rpc('spark', cik, rid, '--days=1')
    #    self.ok(r, "equally spaced points", match="[^ ] {59}\n4m")
    #    rpc('flush', cik, rid)
    #    r = rpc('spark', cik, rid, '--days=1')
    #    self.ok(r, "no data should output nothing", match="")
    #    r = rpc('record', cik, rid, '--value=-1,1', '--value=-62,2', '--value=-3662,3', '--value=-3723,4')
    #    self.ok(r, "record points")
    #    r = rpc('spark', cik, rid, '--days=1')
    #    self.ok(r, "three points, two intervals", match="^[^ ] {58}[^ ]\n1m 1s +1h$")'''

    def _latest(self, cik, rid, val, msg):
        r = rpc('read', cik, rid, '--format=raw')
        self.assertEqual(r.exitcode, 0, 'read succeeded')
        self.l("{0} vs {1}".format(r.stdout, val))
        self.assertEqual(r.stdout, val, msg)

    @attr('script')
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
            'name': 'test測試',
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
                'path': basedir + '/files/helloworld.lua',
                'out': 'line 1: Hello world!',
                'portoutput': 'Hello dataport!'}
        lua1['content'] = open(lua1['path']).read().strip()
        lua2 = {'name': 'helloworld2.lua',
                'path': basedir + '/files/helloworld2.lua',
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
        # test other form
        r = rpc('script', cik, '--file='+lua1['path'], '--name=' + lua1['name'] + '_form2', '--create')
        self.ok(r, 'upload new script with new argument form succeeds')
        self.assertEqual(readscript(cik, lua1['name'] + '_form2'), lua1['content'], 'create script with new argument form')
        # test passing RID
        r = rpc('script', cik, 'scriptByRID', '--file='+lua1['path'], '--name=' + lua1['name'] + '_form2', '--create')
        self.ok(r, 'upload new script with new argument form succeeds')
        self.assertEqual(readscript(cik, lua1['name'] + '_form2'), lua1['content'], 'create script with new argument form')

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

    def usage_t(self):
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
        time.sleep(4)
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
            tz = get_localzone()
            local_time_without_offset = datetime.fromtimestamp(parse_ts(s))
            return str(tz.localize(local_time_without_offset))

        self.ok(r, 'two readings on one timestamp', match=re.escape('{0},,3,0.3'.format(tolocaltz('2013-07-20 03:00:08'))))

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

        rids = [r.strip() for r in rpc('listing', cik, '--types=dataport,datarule', '--plain').stdout.split('\n')]

        # this test could be better -- for now, just verify that the right
        # number of columns come out
        r = rpc('read', '--start=2013-07-20T3:00:08', '--end=2013-07-20T3:00:08', '--timeformat=unix', cik)
        self.ok(r, 'read all RIDs', match='timestamp,' + ','.join(['.*' for rid in rids]) + '\n[0-9]+' + ','.join(['.*' for rid in rids]))

    def clone_test(self):
        '''Clone command'''
        stdports = self._createDataports()
        cik = self.client.cik()

        r = rpc('create', cik, '--type=dataport', '--format=string', '--alias=foo')
        self.ok(r, 'create dataport succeeds')
        r = rpc('write', cik, 'foo', '--value=testvalue')

        def clone_helper(cik, rid, nohistorical=False):
            if nohistorical:
                r = rpc('clone', cik, '--rid=' + rid, '--nohistorical')
            else:
                r = rpc('clone', cik, '--rid=' + rid)
            self.ok(r, 'clone succeeds')
            if 'cik' in r.stdout:
                copyrid, copycik = self._ridcik(r.stdout)
                return copyrid, copycik
            else:
                return copyrid

        # clone client
        copyrid, copycik = clone_helper(self.portalcik, self.client.rid)

        r = rpc('diff', cik, copycik)
        if sys.version_info < (2, 7):
            self.notok(r, 'diff not supported with Python <2.7')
        else:
            self.ok(r, 'diff with clone, no differences', match='')

        r = rpc('read', copycik, 'foo', '--format=raw')
        self.ok(r, 'time series data was copied', match='testvalue')

        copyrid, copycik = clone_helper(self.portalcik, self.client.rid, nohistorical=True)

        r = rpc('diff', cik, copycik)
        if sys.version_info < (2, 7):
            self.notok(r, 'diff not supported with Python <2.7')
        else:
            self.ok(r, 'diff with clone, no differences', match='')

        r = rpc('read', copycik, 'foo', '--format=raw')
        self.ok(r, 'time series data was not copied when --nohistorical was specified', match='')

        # clone dataport
        #copyrid = clone_helper(cik, 'foo')
        #self.ok(r, 'copy a dataport')
        #
        #r = rpc('diff', cik, copycik)
        #if sys.version_info < (2, 7):
        #    self.notok(r, 'diff not supported with Python <2.7')
        #else:
        #    self.ok(r, 'diff after cloning dataport in only one of two clones, notices differences', match='.+')
        #
        #copyrid = clone_helper(copycik, 'foo')
        #self.ok(r, 'copy another dataport')
        #
        #r = rpc('diff', cik, copycik)
        #if sys.version_info < (2, 7):
        #    self.notok(r, 'diff not supported with Python <2.7')
        #else:
        #    self.ok(r, 'diff after cloning dataport in two clones, no differences', match='')'''
        # TODO: test --noaliases

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

        #r = rpc('copy', cik, cik, '--cikonly')
        #self.ok(r, 'copy client into itself', match=self.RE_RID)
        #innercik = r.stdout
        #
        #r = rpc('copy', copycik, copycik, '--cikonly')
        #self.ok(r, 'copy client copy into itself', match=self.RE_RID)
        #innercopycik = r.stdout
        #
        #r = rpc('lookup', innercopycik, 'string_port_alias')
        #self.ok(r, 'lookup dataport on inner cik copy', match=self.RE_RID)
        #innercopydataportrid = r.stdout

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
            'name': 'test測試',
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
        exo = ExolineOnepV1(host=config['host'], port=config['port'], https=config['https'])
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

        r = rpc('--port=80', '--http', 'info', cik)
        self.ok(r, 'valid port and host at command line')

        r = rpc('--https', 'info', cik)
        self.ok(r, 'https connection')

        r = rpc('--port=443', 'info', cik)
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
            self.assertTrue(k in info.keys(), 'should find key {0} when options is empty'.format(k))

        for k in allkeys:
            # include each key
            r = rpc('info', cik, rid, '--include={0}'.format(k))
            self.ok(r, 'info --include={0}'.format(k))
            info = json.loads(r.stdout)
            self.assertTrue(list(info.keys()) == [k], 'only requested key was returned')
            # exclude each key
            r = rpc('info', cik, rid, '--exclude={0}'.format(k))
            self.ok(r, 'info --exclude={0}'.format(k))
            info = json.loads(r.stdout)
            keys = list(info.keys())
            self.assertTrue(len(keys) == len(allkeys) - 1 and k not in keys)

    @attr('read')
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
        if False:
            # cassandra is faster, so this fails
            readcmd = ['--httptimeout=1', 'read', cik, rid1,
                    '--limit={0}'.format(numpts),
                    '--start={0}'.format(start),
                    '--end={0}'.format(end)]
            r = rpc(*(readcmd + ['--chunksize={0}'.format(numpts)]))
            self.notok(r, "read a lot of data with a single big read")

            readcmdchunks = readcmd + ['--chunksize=512']
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

    @attr('read')
    def read_selection_test(self):
        '''Read --selection option'''
        cik = self.client.cik()
        rid = self._createMultiple(cik, [
            Resource(cik, 'dataport', {'format': 'string', 'name': 'string_port'})])[0]
        r = rpc('record', cik, rid, '--value=1,a', '--value=2,a', '--value=3,c', '--value=4,d', '--value=5,e', '--value=8,f')
        self.ok(r, 'record values')
        r = rpc('read', cik, rid, '--start=1', '--end=10', '--timeformat=unix', '--limit=2', '--selection=givenwindow')
        self.ok(r, 'read with --selection set', match=r'8,f\r?\n1,a')

    def utf8_test(self):
        '''Read a string with UTF8 characters'''
        cik = self.client.cik()
        rid1 = self._createMultiple(cik, [
            Resource(cik, 'dataport', {'format': 'string', 'name': 'string_port'})])[0]

        r = rpc('flush', cik, rid1)
        r = rpc('write', cik, rid1, '--value=°C')
        self.ok(r, 'write an UTF8 String')
        r = rpc('read', cik, rid1, '--format=raw')
        self.ok(r, 'read UTF8 string', match='°C')

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
        self.ok(r, 'read two points, ascending', match="1.0\n2.0")

        r = rpc('read', cik, rid, '--limit=2', '--format=raw', '--sort=desc')
        self.ok(r, 'read two points, descending', match="3.0\n2.0")

        r = rpc('read', cik, rid, '--limit=2', '--format=raw')
        self.ok(r, 'read two points, ascending (desc is default)', match="3.0\n2.0")

        r = rpc('read', cik, rid, '--limit=3', '--format=raw', '--sort=desc')
        self.ok(r, 'read two points, descending', match="3.0\n2.0\n1.0")

    def stripcarriage_test(self):
        '''Read command handles carriage-returns correctly'''
        cik = self.client.cik()
        rid = self._createMultiple(
            cik,
            [Resource(cik,
                      'dataport',
                      {'format': 'string', 'name': 'stripcarriage_port'})])[0]

        r = rpc('write', cik, rid, '--value=foo\rbar')
        r = rpc('read', cik, rid, '--limit=1')
        self.ok(r, 'removed carriage return from string', search='foobar')

    def ip_test(self):
        '''ip command'''
        r = rpc('ip', noconfig=True)
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

        r = rpc('data', cik, '--read=float', noconfig=True)
        self.ok(r, 'read dataport with no value', '')

        r = rpc('data', cik + 'a', '--write=float,3.1415', noconfig=True)
        self.notok(r, 'bad cik fails')

        r = rpc('data', cik, '--write=float', noconfig=True)
        self.notok(r, 'bad write format fails')

        r = rpc('data', cik, '--write=float,,2', noconfig=True)
        self.notok(r, 'multiple commas in write fails')

        r = rpc('data', cik, '--write=float,3.1415', noconfig=True)
        self.ok(r, 'write single value', match='')

        r = rpc('data', cik, '--read=float', '--read=integer', noconfig=True)
        self.ok(r, 'read two values, only one of which exists', match='float=3.1415')

        r = rpc('data', cik, '--write=string,foo', '--write=integer,616', noconfig=True)
        self.ok(r, 'write multiple values', match='')

        r = rpc('data', cik, '--read=string', '--read=integer', '--read=float', noconfig=True)
        self.ok(r, 'read multiple values', match='float=3.1415&integer=616&string=foo')

        r = rpc('data', cik, '--read=integer', '--read=float', '--read=string', noconfig=True)
        self.ok(r, 'read multiple values, different order', match='string=foo&float=3.1415&integer=616')

        r = rpc('data', cik, '--read=integer', '--write=float,17.5', '--write=string,bar', '--read=string', noconfig=True)
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

    @attr('spec')
    @attr('script')
    def spec_test(self):
        '''Spec command'''
        print(os.path.dirname(os.getcwd()))
        cik = self.client.cik()
        spec = basedir + '/files/spec.yaml'
        spec_schema = basedir + '/files/spec_schema.yaml'
        r = rpc('spec', cik, spec)
        self.notok(r, 'no ids specified')
        r = rpc('spec', cik, spec, '--ids=1,2')
        self.ok(r, 'specify ids, client doesn''t match', search='not found')
        r = rpc('spec', cik, spec, '--ids=1,2', '--create')
        self.ok(r, 'create dataports and scripts based on spec')
        r = rpc('spec', cik, spec, '--ids=1,2')
        self.ok(r, 'check that client was set up based on spec', match='')

        # test correct number of children of each type
        r = rpc('drop', cik, '--all-children')
        self.ok(r, 'drop children from client')
        # just one id so numbers work out
        r = rpc('spec', cik, spec, '--ids=1', '--create')
        self.ok(r, 'create dataports and scripts based on spec')

        r = rpc('listing', cik, '--types=dataport,datarule')
        self.ok(r, 'get listing of client')
        listing = json.loads(r.stdout)
        dataports = listing['dataport']
        datarules = listing['datarule']

        specobj = yaml.safe_load(open(spec))
        spec_numdataports = len(specobj['dataports'])
        self.assertEqual(len(dataports), spec_numdataports, 'created correct number of dataports')
        spec_numscripts= len(specobj['scripts'])
        self.assertEqual(len(datarules), spec_numscripts, 'created correct number of scripts')

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
        self.assertEqual(meta['datasource']['unit'], '°F', 'unit set correctly based on spec')

        # test format content
        r = rpc('read', cik, 'testjson', '--format=raw')
        self.ok(r, 'read testjson initial value', match='{}')

        # test json schema validation
        r = rpc('drop', cik, '--all-children')
        self.ok(r, 'drop children from test client')
        r = rpc('create', cik, '--type=dataport', '--format=string', '--alias=testschema')
        r = rpc('write', cik, 'testschema', "--value={\"foo\":\"bar\"}")
        self.ok(r, 'write valid json')
        r = rpc('read', cik, 'testschema')
        self.l('stdout: ' + r.stdout)
        r = rpc('spec', cik, spec_schema)
        self.ok(r, 'jsonschema is valid', match='')

        r = rpc('write', cik, 'testschema', "--value={\"bar\":1}")
        self.ok(r, 'write invalid json')
        r = rpc('read', cik, 'testschema')
        self.l('stdout: ' + r.stdout)
        r = rpc('spec', cik, spec_schema)
        self.ok(r, 'jsonschema is not valid', search='is a required property')

        # TODO: test lua script templating
        # TODO: test that correct differences are reported. Change one thing
        # at a time, confirm report is correct, then confirm passing --create
        # resolves it.

        # text --example script
        r = rpc('drop', cik, '--all-children')
        self.ok(r, 'drop children from test client')
        r = rpc('spec', '--example')
        example_spec = basedir + '/files/tmp_examplespec.yaml'
        with open(example_spec, 'w') as f:
            print(r.stdout)
            out = r.stdout
            f.write(out)
        r = rpc('spec', example_spec, '--check')
        self.ok(r, 'example spec passes --check')
        r = rpc('spec', cik, example_spec, '--ids=A,B')
        self.ok(r, 'empty client does not match example spec', match='.+')
        r = rpc('spec', cik, example_spec, '--create', '--ids=A,B')
        self.ok(r, 'create from example spec')
        r = rpc('spec', cik, example_spec, '--ids=A,B')
        self.ok(r, 'client now matches example spec', match='')

        os.remove(example_spec)

    @attr('spec')
    def spec_check_test(self):
        '''Test that invalid spec files are detected'''
        cik = self.client.cik()
        def test_file(filename):
            spec = basedir + '/files/' + filename
            r = rpc('spec', spec, '--check')
            self.notok(r, filename + ' problems are caught by --check', search='problems in spec')
            r = rpc('spec', cik, spec, '--create')
            self.notok(r, filename + ' does not create', search='problems in spec')

        test_file('spec_mistyped_key.yaml')
        test_file('spec_invalid_jsonschema.yaml')
        test_file('spec_missing_keys.yaml')

    @attr('spec')
    def spec_url_test(self):
        '''Pass urls for spec file and spec scripts'''
        cik = self.client.cik()

        def spec_and_check(spec, aliases):
            r = rpc('create', cik, '--type=client', '--name=通過規範', '--cikonly')
            self.ok(r, 'create child client')
            childcik = r.stdout
            r = rpc('spec', childcik, spec, '--create')
            self.ok(r, 'created device from spec url')
            r = rpc('info', childcik, '--include=aliases')
            self.ok(r, 'get info for created device')
            aliases = json.loads(r.stdout)['aliases']
            aliaslist = list(itertools.chain(*[aliases[k] for k in aliases]))
            self.assertTrue(
                all([a in aliaslist for a in ['temp_f', 'temp_c', 'convert.lua']]),
                'created device has the right aliases')

        spec_and_check(
            'https://raw.githubusercontent.com/exosite/exoline/master/test/files/spec_script_url.yaml',
            ['temp_f', 'temp_c', 'convert.lua'])
        spec_and_check(
            'https://raw.githubusercontent.com/exosite/exoline/master/test/files/spec_script_relative_url.yaml',
            ['temp_f', 'temp_c', 'convert.lua'])
        spec_and_check(
            'http://goo.gl/RQzS7d', # spec_script_relative_url.yaml again, this time via redirect
            ['temp_f', 'temp_c', 'convert.lua'])
        # mainly this is testing embedded scripts
        spec_and_check(
            'https://raw.githubusercontent.com/exosite/exoline/master/test/files/spec_script_embedded.yaml',
            ['temp_f', 'temp_c', 'convert.lua'])

    @attr('spec')
    def spec_subscribe_test(self):
        '''Test spec dataports with a subscription to another'''
        cik = self.client.cik()
        spec = basedir + '/files/spec_subscribe.yaml'
        r = rpc('spec', cik, spec, '--create')
        self.ok(r, 'create dataports with subscriptions based on spec')

        # Now see if it did
        r = rpc('write', cik, 'source', '--value=ATEST')
        self.ok(r, 'wrote to source')
        r = rpc('read', cik, 'destination', '--format=raw')
        self.ok(r, 'read subscribed value', match='ATEST')

    @attr('spec')
    def spec_preprocess_test(self):
        '''Test spec dataports with preprocess'''
        cik = self.client.cik()
        spec = basedir + '/files/spec_preprocess.yaml'
        r = rpc('spec', cik, spec, '--create')
        self.ok(r, 'create dataports with subscriptions based on spec')

        # Check the simple one
        r = rpc('write', cik, 'math', '--value=10')
        self.ok(r, 'wrote to source')
        r = rpc('read', cik, 'math', '--format=raw')
        self.ok(r, 'read preprocessed value', match='28.8')

        # Check the complex one
        r = rpc('write', cik, 'variable', '--value=10')
        self.ok(r, 'wrote to variable')
        r = rpc('write', cik, 'complex', '--value=5')
        self.ok(r, 'wrote to complex')
        r = rpc('read', cik, 'complex', '--format=raw')
        self.ok(r, 'read preprocessed value', match='30')

        # Spec matches
        r = rpc('spec', cik, spec)
        self.ok(r, 'check spec and find no differences', match='')

        # modify spec
        spec2 = basedir + '/files/spec_preprocess_2.yaml'
        r = rpc('spec', cik, spec2, '--create')
        self.ok(r, 'modify preprocess to a second spec', match='')
        r = rpc('write', cik, 'math', '--value=10')
        self.ok(r, 'wrote to source')
        r = rpc('read', cik, 'math', '--format=raw')
        self.ok(r, 'read preprocessed value for spec2', match='15.5')
        r = rpc('spec', cik, spec)
        self.ok(r, 'check original spec and find differences', search='preprocess')
        r = rpc('spec', cik, spec2)
        self.ok(r, 'check spec2 and find no differences', match='')


    @attr('spec')
    def spec_retention_test(self):
        '''Test spec dataports with retention'''
        cik = self.client.cik()
        spec = basedir + '/files/spec_retention.yaml'
        r = rpc('spec', cik, spec, '--create')
        self.ok(r, 'create dataports with retention based on spec')

        # Check them
        r = rpc('info', cik, 'A', '--include=description')
        info = json.loads(r.stdout)
        retention = info['description']['retention']
        log.debug(retention)
        self.assertTrue(retention is not None, 'No retention in info')
        self.assertTrue(retention['count'] == 45, 'Count is wrong')
        self.assertTrue(retention['duration'] == 'infinity', 'Duration is wrong')

        r = rpc('info', cik, 'B', '--include=description')
        info = json.loads(r.stdout)
        retention = info['description']['retention']
        log.debug(retention)
        self.assertTrue(retention is not None, 'No retention in info')
        self.assertTrue(retention['count'] == 'infinity', 'Count is wrong')
        self.assertTrue(retention['duration'] == 6000, 'Duration is wrong')

        r = rpc('info', cik, 'C', '--include=description')
        info = json.loads(r.stdout)
        retention = info['description']['retention']
        log.debug(retention)
        self.assertTrue(retention is not None, 'No retention in info')
        self.assertTrue(retention['count'] == 10, 'Count is wrong')
        self.assertTrue(retention['duration'] == 9900, 'Duration is wrong')

        r = rpc('info', cik, 'D', '--include=description')
        info = json.loads(r.stdout)
        retention = info['description']['retention']
        log.debug(retention)
        self.assertTrue(retention is not None, 'No retention in info')
        self.assertTrue(retention['count'] == 'infinity', 'Count is wrong')
        self.assertTrue(retention['duration'] == 'infinity', 'Duration is wrong')

    @attr('spec')
    def spec_multi_test(self):
        '''Test spec --portal for updating multiple devices'''
        # Get example spec
        r = rpc('spec', '--example')
        example_spec = basedir + '/files/tmp_examplespec.yaml'
        with open(example_spec, 'w') as f:
            print(r.stdout)
            out = r.stdout
            f.write(out)


        cik = self.client.cik()

        # meta fields for test devices
        metaMyModel = "{\"device\":{\"type\":\"vendor\",\"model\":\"myModel\",\"vendor\":\"myVendor\"}}"
        metaNotMyModel = "{\"device\":{\"type\":\"vendor\",\"model\":\"NotMyModel\",\"vendor\":\"myVendor\"}}"


        # Create two devices of myModel type,
        myDev1_r = Resource(
            cik,
            'client',
            {"name": "myDev1",
            "meta":metaMyModel})

        myDev2_r = Resource(
            cik,
            'client',
            {"name": "myDev2",
            "meta":metaMyModel})

        # Create one device of notMyModel type
        notMyDev_r = Resource(
            cik,
            'client',
            {"name": "notMyDev",
            "meta":metaNotMyModel})

        # Create once device without a model type
        genericDev_r = Resource(
            cik,
            'client',
            {"name": "genericDev"})


        # Create devices
        myDev1 = self._create(myDev1_r)
        myDev2 = self._create(myDev2_r)
        notMyDev = self._create(notMyDev_r)
        genericDev = self._create(genericDev_r)

        # Attempt to apply spec to myModel types
        r = rpc('spec', cik, example_spec, '--portal', '-f', '--create', '--update-scripts', '--ids=A,B')
        self.ok(r, 'applying spec to portal')

        # make sure that both myDevs now meet spec
        r = rpc('spec', myDev1.cik(), example_spec, '--ids=A,B')
        self.ok(r, "Device 1 didn't match spec", search='')

        r = rpc('spec', myDev2.cik(), example_spec, '--ids=A,B')
        self.ok(r, "Device 2 didn't match spec", search='')

        # and that both the non-example or the one that didn't have
        # a type don't meet the spec.
        r = rpc('spec', notMyDev.cik(), example_spec, '--ids=A,B')
        self.ok(r, "Device didn't match spec", search='not found')

        r = rpc('spec', genericDev.cik(), example_spec, '--ids=A,B')
        self.ok(r, "Device didn't match spec", search='not found')


    @attr('spec')
    def spec_domain_test(self):
        '''
            Test updating multiple devices of the same clientmodel
            under multiple portals that are under a single domain.
        '''
        # Get example spec
        r = rpc('spec', '--example')
        example_spec = basedir + '/files/tmp_examplespec.yaml'
        with open(example_spec, 'w') as f:
            print(r.stdout)
            out = r.stdout
            f.write(out)


        cik = self.client.cik()

        # Create 2 users
        portalOne_r = Resource(
            cik,
            'client',
            {"name": "joe@exosite.com"})

        portalTwo_r = Resource(
            cik,
            'client',
            {"name": "jim@exosite.com"})

        # Create two portals
        portalOne = self._create(portalOne_r)
        portalTwo = self._create(portalTwo_r)

        # meta fields for test devices
        metaMyModel = "{\"device\":{\"type\":\"vendor\",\"model\":\"myModel\",\"vendor\":\"myVendor\"}}"
        metaNotMyModel = "{\"device\":{\"type\":\"vendor\",\"model\":\"NotMyModel\",\"vendor\":\"myVendor\"}}"


        # Create two devices of myModel type,
        myDev1_r = Resource(
            portalOne.cik(),
            'client',
            {"name": "myDev1",
            "meta":metaMyModel})

        myDev2_r = Resource(
            portalOne.cik(),
            'client',
            {"name": "myDev2",
            "meta":metaMyModel})

        # Create one device of notMyModel type
        notMyDev_r = Resource(
            portalOne.cik(),
            'client',
            {"name": "notMyDev",
            "meta":metaNotMyModel})

        # Create once device without a model type
        genericDev_r = Resource(
            portalOne.cik(),
            'client',
            {"name": "genericDev"})

        # Create devices under each portal
        p1_myDev1 = self._create(myDev1_r)
        p1_myDev2 = self._create(myDev2_r)
        p1_notMyDev = self._create(notMyDev_r)
        p1_genericDev = self._create(genericDev_r)

        # set parent cik of resources to portal 2
        myDev1_r.parentcik = portalTwo.cik()
        myDev2_r.parentcik = portalTwo.cik()
        notMyDev_r.parentcik = portalTwo.cik()
        genericDev_r.parentcik = portalTwo.cik()

        # create devices under portal 2
        p2_myDev1 = self._create(myDev1_r)
        p2_myDev2 = self._create(myDev2_r)
        p2_notMyDev = self._create(notMyDev_r)
        p2_genericDev = self._create(genericDev_r)

        # Portal 1
        # Attempt to apply spec to myModel types
        r = rpc('spec', cik, example_spec, '--domain', '-f', '--create', '--update-scripts', '--ids=A,B')
        self.ok(r, 'applying spec to portal')

        # make sure that both myDevs now meet spec
        r = rpc('spec', p1_myDev1.cik(), example_spec, '--ids=A,B')
        self.ok(r, "P1 Device 1 didn't match spec", search='')

        r = rpc('spec', p1_myDev2.cik(), example_spec, '--ids=A,B')
        self.ok(r, "P1 Device 2 didn't match spec", search='')

        # and that both the non-example or the one that didn't have
        # a type don't meet the spec.
        r = rpc('spec', p1_notMyDev.cik(), example_spec, '--ids=A,B')
        self.ok(r, "P1 Device didn't match spec", search='not found')

        r = rpc('spec', p1_genericDev.cik(), example_spec, '--ids=A,B')
        self.ok(r, "P1 Device didn't match spec", search='not found')

        # Portal 2
        # make sure that both myDevs now meet spec
        r = rpc('spec', p2_myDev1.cik(), example_spec, '--ids=A,B')
        self.ok(r, "P2 Device 1 didn't match spec", search='')

        r = rpc('spec', p2_myDev2.cik(), example_spec, '--ids=A,B')
        self.ok(r, "P2 Device 2 didn't match spec", search='')

        # and that both the non-example or the one that didn't have
        # a type don't meet the spec.
        r = rpc('spec', p2_notMyDev.cik(), example_spec, '--ids=A,B')
        self.ok(r, "P2 Device didn't match spec", search='not found')

        r = rpc('spec', p2_genericDev.cik(), example_spec, '--ids=A,B')
        self.ok(r, "P2 Device didn't match spec", search='not found')

    def portals_cache_test(self):
        '''Portals clearcache command and option'''
        cik = self.client.cik()

        # just make sure the command doesnt throw an exception
        r = rpc('--clearcache',
                'create',
                cik,
                '--type=client',
                '--name=portals_visible')
        self.ok(r, 'create a client and clear portals cache')
        # TODO: verify client displays in Portals

        r = rpc('-e',
                '--portals=https://weaver.exosite.com',
                'create',
                cik,
                '--type=client',
                '--name=portals_visible2')
        self.ok(r, 'create a client and clear portals cache with portals server specified')
        # TODO: verify client displays in Portals

        r = rpc('portals', 'clearcache', cik)
        self.ok(r, 'invalidate cache, no procedure specified')

        # TODO: test each procedure
        r = rpc('portals', 'clearcache', cik, 'create', 'update')
        self.ok(r, 'invalidate cache, a couple of procedures specified')

        r = rpc('--portals=https://weaver.exosite.com', 'portals', 'clearcache', cik, 'drop')
        self.ok(r, 'invalidate cache portals server specified')

        r = rpc('--portals=https://portals.exosite.comm', 'portals', 'clearcache', cik, 'create', 'update')
        self.notok(r, 'invalid portals server specified')

    def lookup_owner_test(self):
        '''Lookup --owner-of variant'''
        cik = self.client.cik()

        daughter = self._create(
            Resource(cik, 'client',
                {'name': 'Daughter'}))

        granddaughter = self._create(
            Resource(daughter.cik(), 'dataport',
                      {'format': 'float', 'name': 'Original Name'}))

        r = rpc('lookup', cik, '--owner-of=' + granddaughter.rid)
        self.ok(r, 'owner lookup succeeds', match=daughter.rid)

    def share_test(self):
        '''Sharing commands: share, revoke, lookup --share, deactivate, listing --filter=activated'''
        cik = self.client.cik()

        r = rpc('create', cik, '--type=client', '--cikonly')
        self.ok(r, 'create child 1')
        childcik1 = r.stdout

        r = rpc('create', cik, '--type=client', '--cikonly')
        self.ok(r, 'create child 2')
        childcik2 = r.stdout

        r = rpc('create', cik, '--type=client', '--cikonly')
        self.ok(r, 'create child 3')
        childcik3 = r.stdout

        r = rpc('create', cik, '--type=client', '--cikonly')
        self.ok(r, 'create child 4')
        childcik4 = r.stdout

        dataport_rid1, dataport_rid2 = self._createMultiple(
            childcik1,
            [Resource(childcik1, 'dataport', {'name': 'dataport1',
                                              'format': 'string'}),
             Resource(childcik1, 'dataport', {'name': 'dataport2',
                                              'format': 'string'})])

        # share the dataport with client2
        r = rpc('share', childcik1, dataport_rid1)
        self.ok(r, 'share dataport')
        share_code = r.stdout

        r = rpc('activate', childcik2, '--share=' + share_code)
        self.ok(r, 'activate share', match='')

        r = rpc('activate', childcik3, '--share=' + share_code)
        self.notok(r, 'activate share again fails due to count')

        value = 'shared value'
        r = rpc('write', childcik1, dataport_rid1, '--value=' + value)
        r = rpc('read', childcik2, dataport_rid1, '--format=raw')
        self.ok(r, 'read value over share', match=value)

        r = rpc('write', childcik2, dataport_rid1, '--value=' + value)
        self.notok(r, 'write to activated share from non-owner')

        r = rpc('listing', childcik2, '--plain')
        self.ok(r, 'no owned items in listing', match='')

        r = rpc('listing', childcik2, '--filters=activated', '--plain')
        self.ok(r, 'one share in activated listing', match=dataport_rid1)

        r = rpc('tree', childcik2)
        self.ok(r, 'tree with share succeeds')
        self.assertTrue(
            re.search('.*{0}.*share: True.*'.format(dataport_rid1), r.stdout) is not None)

        r = rpc('twee', childcik2, '--rids')
        self.ok(r, 'twee with share succeeds')
        self.assertTrue(
            re.search('.*{0}.*(share).*'.format(dataport_rid1), r.stdout) is not None)

        r = rpc('deactivate', childcik2, '--share=' + share_code)
        self.ok(r, 'deactivate share from client that activated')

        # test revoke
        r = rpc('share', childcik1, dataport_rid1)
        self.ok(r, 'get another share code')
        share_code=r.stdout

        r = rpc('revoke', childcik1, '--share=' + share_code)
        self.ok(r, 'revoke share code')

        r = rpc('activate', childcik3, '--share=' + share_code)
        self.notok(r, 'activate a code that has been revoked')

        # test --meta
        r = rpc('share',
                childcik1,
                dataport_rid1,
                '--meta="This is share metadata"')
        self.ok(r, 'get a share code and set metadata')
        share_code=r.stdout

        r = rpc('share',
                childcik1,
                dataport_rid1,
                '--meta="This is updated share metadata"',
                '--share=' + share_code)
        self.ok(r, 'update share metadata')

        r = rpc('lookup',
                childcik1,
                '--share=' + share_code)
        self.ok(r, 'look up RID for share_code', match=dataport_rid1)

    def read_speed_test(self):
        '''Read speed test'''
        cik = self.client.cik()

        self._createMultiple(
            cik,
            [Resource(cik, 'dataport',
                      {'name': 'dp1',
                       'format': 'string'},
                      alias='dp1')])
        r = rpc('write', cik, 'dp1', '--value=foo')
        self.ok(r, 'write a value')

        start = time.time()
        r = rpc('read', cik, 'dp1')
        end = time.time()
        self.ok(r, 'read a value')
        self.assertTrue(end - start < 3, 'read should not be slow')


    def flush_test(self):
        '''Flush command'''
        cik = self.client.cik()

        self._createMultiple(
            cik,
            [Resource(cik, 'dataport',
                      {'name': 'dp1',
                       'format': 'string'},
                      alias='dp1')])

        r = rpc('record', cik, 'dp1', '--value=1391205573,str1', '--value=1391206208,str2', '--value=1391206232,str3')
        self.ok(r, 'record some values')
        r = rpc('flush', cik, 'dp1')
        self.ok(r, 'flush all points')
        r = rpc('read', cik, 'dp1', '--limit=3', '--sort=asc')
        self.ok(r, 'points were flushed', match='')

        r = rpc('record', cik, 'dp1', '--value=1391205573,str1', '--value=1391206208,str2', '--value=1391206232,str3')
        self.ok(r, 'record values')
        r = rpc('flush', cik, 'dp1', '--start=1391206208')
        self.ok(r, 'flush with a start time')
        r = rpc('read', cik, 'dp1', '--limit=3', '--format=raw', '--sort=asc')
        self.ok(r, 'points were flushed', match='str1\nstr2')

        r = rpc('record', cik, 'dp1', '--value=1391206232,str3')
        self.ok(r, 'record values')
        r = rpc('flush', cik, 'dp1', '--end=1391206208')
        self.ok(r, 'flush with a end time')
        r = rpc('read', cik, 'dp1', '--limit=3', '--format=raw', '--sort=asc')
        self.ok(r, 'points were flushed', match='str2\nstr3')

        r = rpc('record', cik, 'dp1', '--value=1391205573,str1')
        self.ok(r, 'record values')
        r = rpc('flush', cik, 'dp1', '--start=1391206207', '--end=1391206233')
        self.ok(r, 'flush with both start and end time')
        r = rpc('read', cik, 'dp1', '--limit=3', '--format=raw', '--sort=asc')
        self.ok(r, 'points were flushed', match='str1')

    def discreet_test(self):
        '''--discreet option'''
        cik = self.client.cik()
        r = rpc('--discreet', 'tree', cik)
        # this is perhaps masking an issue.
        if sys.version_info < (3, 0):
            r.stdout = r.stdout.decode('utf-8')
        self.ok(r, search='cik: ' + cik[:20] + '01234567890123456789')

    def _createModel(self):
        cik = self.client.cik()

        childrid = self._createMultiple(cik, [
            Resource(cik, 'client', {'name': '你好世界'})])[0]

        # create a model
        id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
        model = 'exolinetestmodel' + id

        pop.model_create(config['vendortoken'], model, childrid,
            aliases=True,
            comments=True,
            historical=True)

        return model, childrid

    def provision_model_test(self):
        '''Provision model command'''
        model, modelrid = self._createModel()

        # list models
        r = prv('model', 'list')
        self.ok(r, 'model is listed', search=model)

        # get info for model
        r = prv('model', 'info', model)
        self.ok(r, 'model info includes RID', search=modelrid)

    def provision_unknown_command(self):
        '''Provision unknown subcommand'''
        r = prv('blarg')
        self.notok(r, 'unknown command', search='blarg')

    def provision_sn_test(self):
        '''Provision sn command'''
        cik = self.client.cik()
        model, modelrid = self._createModel()

        sn = 'sn' + model

        # add sn
        r = prv('sn', 'add', model, sn)
        self.ok(r, 'add sn')

        # list sn
        r = prv('sn', 'list', model)
        self.ok(r, 'list sn', match=sn)

        # enable. This creates a clone in a particular portal,
        # associates it with a serial number, and opens a 24
        # hour window for device activation.
        r = prv('sn', 'enable', model, sn, cik)
        self.ok(r, 'enable sn/create a new clone')

        clonerid = r.stdout.strip()
        r = rpc('info', cik, clonerid, '--include=description,basic')
        self.ok(r, 'info on clone before activation')
        info = json.loads(r.stdout)
        meta = json.loads(info['description']['meta'])
        self.assertEqual(meta['device']['vendor'], config['vendor'], 'clone meta vendor is correct')
        self.assertEqual(meta['device']['model'], model, 'clone meta model is correct')
        self.assertEqual(meta['device']['sn'], sn, 'clone meta sn is correct')
        self.assertEqual(info['basic']['status'], 'notactivated', 'clone is not activated')

        # activate (this would normally be done by a device)
        r = prv('sn', 'activate', model, sn)
        self.ok(r, 'activate sn', match=self.RE_RID)
        clonecik = r.stdout.strip()

        r = rpc('info', clonecik, '--include=description,basic')
        self.ok(r, 'info on device cloned from model')
        info = json.loads(r.stdout)

        self.assertEqual(info['basic']['status'], 'activated',
                         'clone is now activated')

        # regenerate
        r = prv('sn', 'regen', model, sn)
        self.ok(r, 'regenerate CIK', match='')
        time.sleep(1)
        r = rpc('info', clonecik, '--include=basic')
        self.notok(r, 'info fails on previous cik', search='401')
        r = rpc('info', cik, clonerid, '--include=basic')
        self.ok(r, 'info succeeds')
        info = json.loads(r.stdout)
        self.assertEqual(info['basic']['status'], 'notactivated', 'status after regen');
        r = prv('sn', 'activate', model, sn)
        self.ok(r, 're-activate', match=self.RE_RID)
        newcik = r.stdout.strip()
        self.assertNotEqual(clonecik, newcik)
        r = rpc('info', newcik, '--include=basic')
        self.ok(r, 'info succeeds on new, re-activated cik')

        # disable
        r = prv('sn', 'disable', model, sn)
        self.ok(r, 'disable client', match='')
        r = rpc('info', cik, clonerid, '--include=basic')
        self.ok(r, 'info succeeds')
        info = json.loads(r.stdout)
        self.assertEqual(info['basic']['status'], 'expired', 'status after disable');
        r = prv('sn', 'regen', model, sn)
        self.ok(r, 'regenerate CIK', match='')
        r = prv('sn', 'activate', model, sn)
        self.ok(r, 're-activate', match=self.RE_RID)
        newcik = r.stdout.strip()
        r = rpc('info', cik, clonerid, '--include=basic')
        self.ok(r, 'info succeeds')
        info = json.loads(r.stdout)
        self.assertEqual(info['basic']['status'], 'activated', 'status after activate');

        # delete sn
        r = prv('sn', 'delete', model, sn)
        self.ok(r, 'sn is deleted')
        r = prv('sn', 'list', model)
        self.ok(r, 'list sn after deletion')
        self.assertTrue(sn not in r.stdout,
                        'deleted serial number is not in listing')

        # test two ways of adding multiple serial numbers at once
        r = prv('sn', 'add', model, '--file=test/files/serialnumbers')
        self.ok(r, 'add a file full of serial numbers')
        r = prv('sn', 'add', model, '011', '012')
        self.ok(r, 'add multiple serial numbers at command line')
        # load serial numbers a page at a time
        r = prv('sn', 'list', model, '--limit=6')
        self.ok(r, 'get first page of serial numbers',
                match='\n'.join(['[0-9]{3}' for n in range(6)]))
        r2 = prv('sn', 'list', model, '--offset=6')
        self.ok(r2, 'get second page of serial numbers',
                match='\n'.join(['[0-9]{3}' for n in range(6, 12)]))
        sns = sorted((r.stdout + '\n' + r2.stdout).split('\n'))
        self.assertEquals(sns, ['{0:03d}'.format(n + 1) for n in range(12)],
                          'full list of serial numbers matches')
        r = prv('sn', 'delete', model, '--file=test/files/serialnumbers')
        self.ok(r, 'delete serial numbers with --file')
        r = prv('sn', 'delete', model, '011', '012')
        self.ok(r, 'delete the remaining serial numbers')
        r = prv('sn', 'list', model)
        self.ok(r, 'list of serial numbers is empty', match='')

        # test ranges
        r = prv('sn', 'ranges', model)
        self.ok(r, 'list of ranges is empty', match='')
        prefix = '01:02:03:04:05:'
        rangeinfo = ['mac:48', prefix + '00', prefix + 'ff']
        r = prv('sn', 'addrange', model, *rangeinfo)
        self.ok(r, 'add range of mac addresses')
        r = prv('sn', 'ranges', model)
        self.ok(r, 'list ranges after adding one')
        ranges = json.loads(r.stdout)
        self.assertEqual(len(ranges), 1, 'one range in list')
        self.assertEqual(
            ranges[0],
            {"format":"mac:48","length":None,"casing":"upper","first":1108152157440,"last":1108152157695},
            'range looks right in list')
        r = prv('sn', 'delrange', model, *rangeinfo)
        r = prv('sn', 'ranges', model)
        self.ok(r, 'list of ranges is empty', match='')

    def provision_content_test(self):
        '''Provision content commands'''

        # create a model
        model, rid = self._createModel()

        # list content
        r = prv('content', 'list', model)
        self.ok(r, 'no content was listed', match='')

        def content(file, id, type, protected=None):
            args = ['content', 'put', model, id, file, '--meta=thisissometa']
            if protected is not None:
                args.append('--protected=' + protected)

            # put content
            r = prv(*args)
            self.ok(r, 'put content', match='')

            # list content
            r = prv('content', 'list', model)
            self.ok(r, 'model was listed', match=id)

            protectedTest = 'false' if protected is None else protected
            r = prv('content', 'list', model, '--long')
            self.ok(r, 'protected defaults to false', match=id + '.*,' + protectedTest + ',.*')

            # get content info
            r = prv('content', 'info', model, id)
            # e.g. application/octet-stream,1024,1416147370,,false
            self.ok(r,
                    'got content info',
                    match=type + ',[0-9]+,[0-9]+,thisissometa,(true|false)')

            # get content blob
            r = prv('content', 'get', model, id, 'content')
            self.ok(r, 'get content', match='')

            # files should match
            self.assertTrue(filecmp.cmp(file, 'content', shallow=False),
                            'content files match')

            # delete content
            r = prv('content', 'delete', model, id)
            self.ok(r, 'deleted content', match='')
            r = prv('content', 'list', model)
            self.ok(r, 'list content after deletion')
            self.assertTrue(id not in r.stdout)
            r = prv('content', 'info', model, id)
            self.notok(r, 'no info found', search='404 Not Found')


        # test various file types
        content('test/files/content.json', 'content.json', 'application/json')
        content('test/files/content.json', 'content.json', 'application/json', protected='true')
        content('test/files/content.json', 'content.json', 'application/json', protected='false')
        # TODO: get binary files working. Seems to work
        # at the command line, but not from the test.
        #content('test/files/content.bin', 'content.bin', 'application/octet-stream')

    def help_test(self):
        '''Test -h for all commands'''
        def check_help(r, command):
            self.ok(r, 'error exit code')
            self.assertTrue(
                re.search(command, r.stdout, re.MULTILINE) is not None,
                'help text is returned (no error)')
            self.assertTrue(
                re.search('Usage:', r.stdout, re.MULTILINE) is not None,
                'help text includes usage')
            # other linting goes here

        def hlp(args):
            a = args + ['-h']
            r = rpc(*a)
            self.l(args[-1] if len(args) > 0 else 'exo')
            check_help(r, args[-1] if len(args) > 0 else 'exo')
            # this assumes commands are followed by two newlines
            # and then another section
            cmd_section = re.search(r'Commands:\n(.+)\n\n([A-Z]+)',
                                    r.stdout,
                                    flags=re.MULTILINE|re.DOTALL)
            if cmd_section is None:
                # no subcommands
                #self.l(r.stdout)
                self.assertTrue(
                    'Commands:' not in r.stdout,
                    'no commands matched, so we shouldn\'t have a command section')
                return
            else:
                # there are subcommands
                commands = []
                for line in cmd_section.groups()[0].split('\n'):
                    # pull just the command, e.g. 'tree'
                    match = re.match('  ([^-\s][^\s]*)\s.*', line)
                    if match is not None:
                        commands.append(match.groups()[0])
                if len(commands) == 0:
                    self.l(str(commands))

                self.assertTrue(len(commands) > 0)
                for command in commands:
                    hlp(args + [command])

        hlp([])

    def search_test(self):
        '''Search command'''
        cik = self.client.cik()

        childrids = self._createMultiple(cik, [
            Resource(cik, 'client', {'name': '你好' + str(i)}) for i in range(10)])


        #for rid in childrids:
        #    childcik = rpc('lookup', cik, rid, '--cikonly').stdout
        #    ridFloat, ridString = self._createMultiple(childcik, [
        #        Resource(cik, 'dataport', {'format': 'float', 'name': 'should not match'}),
        #        Resource(cik, 'dataport', {'format': 'string', 'name': 'also should not match'})])

        r = rpc('info', cik, childrids[4], '--cikonly')
        self.ok(r, 'look up one of the clients', match=self.RE_RID)
        childcik = r.stdout

        ridFloat, ridString, ridInteger, ridScript = self._createMultiple(childcik, [
            Resource(cik, 'dataport', {'format': 'float', 'name': 'float_port'}, alias='float_alias'),
            Resource(cik, 'dataport', {'format': 'string', 'name': 'string_port'}, alias='string_alias'),
            Resource(cik, 'dataport', {'format': 'integer', 'name': 'integer_port'}, alias='int3ger_alias'),
            Resource(cik, 'datarule', {
                    'format': 'string',
                    'name': 'script_port',
                    'preprocess': [],
                    'rule': {
                        'script': 'debug("你好World")'
                    },
                    'visibility': 'parent',
                    'retention': {
                        'count': 'infinity',
                        'duration': 'infinity'
                    }
                }, alias='script_alias')])

        # set up a device clone with a serial number
        model = 'exolinetestmodel' + ''.join(random.choice(string.digits) for _ in range(5))
        pop.model_create(config['vendortoken'], model, childrids[4],
            aliases=True,
            comments=True,
            historical=True)
        sn = '123456'
        # add sn
        r = prv('sn', 'add', model, sn)
        self.ok(r, 'add sn')
        r = prv('sn', 'enable', model, sn, cik)
        self.ok(r, 'enable sn/create a new clone')
        clonerid = r.stdout.strip()
        # activate (this would normally be done by a device)
        r = prv('sn', 'activate', model, sn)
        self.ok(r, 'activate sn', match=self.RE_RID)
        clonecik = r.stdout.strip()

        # search for name
        r = rpc('search', cik, '你.3')
        self.ok(r, 'search for name', search='你好3')
        childcik3 = rpc('info', cik, childrids[3], '--cikonly').stdout
        self.ok(r, search=childcik3)
        self.assertEqual(len(r.stdout.split('\n')), 1, 'exactly one match')

        # search for alias
        #r = rpc('search', cik, '[a-z]+_ALIAS', '--silent')
        #self.ok(r, search='float_alias')
        #self.ok(r, search='string_alias')
        #self.assertNotIn('int3ger', r.stdout)

        # search with match case
        r = rpc('search', cik, 'Alias', '--matchcase')
        self.ok(r, 'no response with --matchcase', match='')

        # search for script content
        r = rpc('search', cik, 'World', '--matchcase')
        self.ok(r, 'script matches', search='debug\("')

        # search for serial number
        # why is this not working? It works at the command line.
        #r = rpc('search', cik, sn, '--silent')
        #self.l('stderr is: ' + r.stderr)
        #self.l('stdout is: ' + r.stdout)
        #self.ok(r, 'serial number found', search=sn)
        #self.ok(r, 'correct cik in match', search=cik)
        #self.assertEqual(len(r.stdout.split('\n')), 1, 'exactly one serial number match')

        r = rpc('search', cik, '你.4')
        self.ok(r, search='你好4')
        self.l(r.stdout)
        self.assertEqual(len(r.stdout.split('\n')), 2, 'two matches: client model and clone')

    def dump_test(self):
        '''Dump command'''
        cik = self.client.cik()
        childrids = self._createMultiple(cik, [
            Resource(cik, 'client', {'name': '你好' + str(i), 'alias': '你' + str(i)}) for i in range(10)])

        # add some more things to one of the children
        childrid = childrids[4]
        r = rpc('info', cik, childrid, '--cikonly')
        self.ok(r, 'look up one of the clients', match=self.RE_RID)
        childcik = r.stdout

        ridClient, ridFloat, ridString, ridInteger, ridScript = self._createMultiple(childcik, [
            Resource(cik, 'client', {'name': '好'}),
            Resource(cik, 'dataport', {'format': 'float', 'name': 'float_port'}, alias='float_alias'),
            Resource(cik, 'dataport', {'format': 'string', 'name': 'string_port'}, alias='string_alias'),
            Resource(cik, 'dataport', {'format': 'integer', 'name': 'integer_port'}, alias='int3ger_alias'),
            Resource(cik, 'datarule', {
                    'format': 'string',
                    'name': 'script_port',
                    'preprocess': [],
                    'rule': {
                        'script': 'local i = 0'
                    },
                    'visibility': 'parent',
                    'retention': {
                        'count': 'infinity',
                        'duration': 'infinity'
                    }
                }, alias='script_alias')])

        startts = 1418831000
        valsFloat = [[i, 3.14159] for i in range(startts, startts + 250)]
        r = rpc('record', childcik, ridFloat, *['--value={0},{1}'.format(t, v) for t, v in valsFloat])
        self.ok(r, 'record floats')
        valsString = [[i, '你好'] for i in range(startts, startts + 10)]
        r = rpc('record', childcik, ridString, *['--value={0},{1}'.format(t, v) for t, v in valsString])
        self.ok(r, 'record string')
        valsInteger = [[i, 42] for i in range(startts, startts + 10)]
        r = rpc('record', childcik, ridInteger, *['--value={0},{1}'.format(t, v) for t, v in valsInteger])
        self.ok(r, 'record integer')

        dumpfile = 'testdump.zip'
        r = rpc('dump', cik, dumpfile)
        self.ok(r, 'dump')

        def extract_zip(input_zip):
            input_zip = zipfile.ZipFile(input_zip)
            l = [(name, json.loads(input_zip.read(name).decode("utf-8"))) for name in input_zip.namelist()]
            return dict(l)

        dumpzip = extract_zip(dumpfile)
        it = dumpzip['infotree.json']
        self.assertEqual(it['info']['key'], cik, 'key matches')

        def findChild(infotree, rid):
            for r in infotree['info']['children']:
                if r['rid'] == rid:
                    return r
            return None

        def testChildResource(infotree, rid, name, vals=None, alias=None):
            r = findChild(infotree, rid)
            self.assertNotEqual(r, None, 'find child ' + name)
            # test name
            self.assertEqual(r['info']['description']['name'], name, 'name matches')
            # test alias
            if alias is not None:
                self.assertTrue(type(infotree['info']['aliases']) is dict, 'aliases is dict')
                self.assertTrue(alias in infotree['info']['aliases'][rid], 'alias ' + alias + ' is found')
            # test datapoints
            if vals is not None:
                dumpVals = dumpzip[r['info']['basic']['type'] + '.' + rid + '.json']
                self.assertEqual(vals, dumpVals, 'dumped data points match for ' + name)

        self.assertEqual(it['rid'], self.client.rid, 'root rid')
        testChildResource(it, rid=childrid, name='你好4')
        childit = findChild(it, childrid)
        testChildResource(childit, rid=ridFloat, name='float_port', vals=valsFloat, alias='float_alias')
        testChildResource(childit, rid=ridString, name='string_port', vals=valsString, alias='string_alias')
        testChildResource(childit, rid=ridInteger, name='integer_port', vals=valsInteger, alias='int3ger_alias')
        testChildResource(childit, rid=ridScript, name='script_port', vals=[])


def tearDownModule(self):
    '''Do final things'''
    with open('test/testperf.json', 'w') as f:
        f.write(json.dumps(exo.PERF_DATA))
    if 'vendortoken' in config:
        # delete test models
        response = pop.model_list(config['vendortoken'])
        models = response.body.splitlines()
        for model in models:
            if model.startswith('exolinetestmodel'):
                response = pop.model_remove(config['vendortoken'], model)
    # drop all test clients
    rpc('drop', config['portalcik'], '--all-children')
