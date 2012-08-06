# -*- coding: utf-8 -*-

from twisted.trial import unittest

from TwCAS.util import mailboxpv
from TwCAS import ECA

class MockDataRequest(object):
    def __init__(self, **kws):
        for k,v in kws.iteritems():
            setattr(self, k ,v)
        self.reset()
    def reset(self):
        self.result, self.eca = None, None
        self.complete = False
    def error(self, eca):
        self.eca = eca
    def update(self, data, dcount, eca=None):
        self.result = (data, dcount)
        self.eca = eca
    def finish(self):
        self.complete = True

class TestBasic(unittest.TestCase):
    
    def setUp(self):
        self.pv = mailboxpv.MailboxPV(firstdbf=1)

    def test_geterr(self):
        R = MockDataRequest(dbr=5)
        
        self.pv.get(R)

        self.assertEqual(R.eca, ECA.ECA_NOCONVERT)

    def test_get(self):
        R = MockDataRequest(dbr=1, dcount=1, dynamic=False)
        
        self.pv.get(R)

        self.assertEqual(R.eca, None)
        self.assertEqual(R.result, ('\0'*8, 1))

    def test_put(self):
        R = MockDataRequest()
        
        data = '\1\2'

        self.pv.put(0, 1, data, R)
        
        self.assertTrue(R.complete)

        self.assertEqual(self.pv.dbf, 0)
        self.assertEqual(self.pv.value, data)
        self.assertEqual(self.pv.count, 1)

    def test_putdifferent(self):
        R = MockDataRequest()
        
        data = '\x00\x01\x02\x03\x00\x01\x02\x03'

        self.pv.put(5, 2, data, R)
        
        self.assertTrue(R.complete)

        self.assertEqual(self.pv.dbf, 5)
        self.assertEqual(self.pv.value, data)
        self.assertEqual(self.pv.count, 2)

    def test_monitor(self):
        M1 = MockDataRequest(dbr=1, dcount=1, dynamic=False)
        M2 = MockDataRequest(dbr=1, dcount=0, dynamic=True)
        M3 = MockDataRequest(dbr=1, dcount=3, dynamic=False)

        self.pv.monitor(M1)
        self.pv.monitor(M2)
        self.pv.monitor(M3)

        self.assertEqual(M1.eca, None)
        self.assertEqual(M1.result, ('\0'*8, 1))
        M1.reset()
        self.assertEqual(M2.eca, None)
        self.assertEqual(M2.result, ('\0'*8, 1))
        M2.reset()
        self.assertEqual(M3.eca, None)
        self.assertEqual(M3.result, ('\0'*8, 3))
        M3.reset()

        self.pv.put(1, 2, '\1\2\3\4', None)

        # only the first element
        self.assertEqual(M1.eca, None)
        self.assertEqual(M1.result, ('\1\2\0\0\0\0\0\0', 1))

        # both elements
        self.assertEqual(M2.eca, None)
        self.assertEqual(M2.result, ('\1\2\3\4\0\0\0\0', 2))

        # both elements and a padding element
        self.assertEqual(M3.eca, None)
        self.assertEqual(M3.result, ('\1\2\3\4\0\0\0\0', 3))

    def test_monitorerror(self):
        M1 = MockDataRequest(dbr=4, dcount=1, dynamic=False)
        M2 = MockDataRequest(dbr=1, dcount=1, dynamic=False)

        self.pv.monitor(M1)
        self.pv.monitor(M2)

        self.assertEqual(M1.eca, ECA.ECA_NOCONVERT)
        M1.reset()
        self.assertEqual(M2.eca, None)
        self.assertEqual(M2.result, ('\0'*8, 1))
        M2.reset()

        self.pv.put(4, 1, '\x42', None)

        self.assertEqual(M1.eca, None)
        self.assertEqual(M1.result, ('\x42\0\0\0\0\0\0\0', 1))

        self.assertEqual(M2.eca, ECA.ECA_NOCONVERT)
