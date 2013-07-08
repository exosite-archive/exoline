"""Exoline test
   Tests exoline commands. Requires portalcik to be set in config.py.

Usage:
  test.py <portal-cik>
""" 
import sys
import json
import re
import time
from unittest import TestCase

from scripttest import TestFileEnvironment
from docopt import docopt 
import nose

try:
    from testconfig import config
except:
    sys.stderr.write("Please copy testconfig.py.template to testconfig.py and set portalcik.")

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
    env = TestFileEnvironment('./tmp')
    prg = '../../bin/exo'

    # test client
    cl = None

    def _rid(self, s):
        '''Parse rid from s, raising an exception if it doesn't validate.'''
        m = re.match("^([a-zA-Z0-9]{40}).*", s)
        self.assertFalse(m is None)
        return m.groups()[0] 

    def _create(self, res):
        '''Creates a resource at the command line.'''
        r = self.env.run(
            "{} create {} --type={} -".format(
            self.prg, res.parentcik, res.type), 
            stdin=json.dumps(res.desc))
        rid = self._rid(r.stdout)
        r = self.env.run(
            '{} info {} {}'.format(
            self.prg, res.parentcik, rid))
        info = json.loads(r.stdout.strip())
        res.created(rid, info) 
        print("Created {}, rid: {}".format(res.type, res.rid))
        return res 
       
    def setUp(self):
        '''Create some devices in the portal to test'''
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
        self.env.run('{} drop {} {}'.format(self.prg, self.portalcik, self.client.rid))
        pass

    def _writeAndRead(self, res):
        if res.write is not None:
            cik = res.parentcik
            rid = res.rid
            for value in res.write:
                r = self.env.run(
                    "{} write {} {} --value={}".format(
                        self.prg, cik, rid, value))
                time.sleep(1)

            r = self.env.run(
                "{} read {} {} --limit={}".format(
                    self.prg, cik, rid, len(res.write)))
            wroteValues = [unicode(v) for v in res.write]
            lines = r.stdout.split('\n')
            readValues = [line.split(',')[1] 
                for line in lines if len(line.strip()) > 0]
            readValues.reverse()
            print 'Wrote {}'.format(wroteValues)
            print 'Read {}'.format(readValues)
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


