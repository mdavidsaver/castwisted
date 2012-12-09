# -*- coding: utf-8 -*-

from twisted.trial import unittest

from twisted.internet.defer import Deferred, inlineCallbacks

from TwCAS.util import pvs
from TwCAS import ECA
from TwCAS.dbr import DBF, DBR, DBE, dbr_info

class MockDataRequest(object):
    def __init__(self, **kws):
        for k,v in kws.iteritems():
            setattr(self, k ,v)
        self.reset()
    def reset(self):
        self.waiter = Deferred()
        self.result, self.eca = None, None
        self.complete = False
    def error(self, eca):
        self.eca = eca
        self.complete = True
        self.waiter.callback(eca==ECA.ECA_NORMAL)
    def update(self, data, dcount, eca=None):
        self.result = (data, dcount)
        self.eca = eca
        self.waiter.callback(eca==ECA.ECA_NORMAL)
    def finish(self):
        self.error(ECA.ECA_NORMAL)

class TestDynamic(unittest.TestCase):
    
    def setUp(self):
        self.pv = pvs.DynamicMailboxPV(firstdbf=1)

    def test_geterr(self):
        R = MockDataRequest(dbr=5)
        
        self.pv.get(R)

        self.assertEqual(R.eca, ECA.ECA_NOCONVERT)

    def test_get(self):
        R = MockDataRequest(dbr=1, dcount=1)
        
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
        M1 = MockDataRequest(dbr=1, dcount=1)

        self.pv.monitor(M1)

        self.assertEqual(M1.eca, None)
        self.assertEqual(M1.result, ('\0'*8, 1))
        M1.reset()

        self.pv.put(1, 2, '\1\2\3\4', None)

        # only the first element
        self.assertEqual(M1.eca, None)
        self.assertEqual(M1.result, ('\1\2\3\4\0\0\0\0', 2))

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

class TestNumeric(unittest.TestCase):
    timeout = 1
    
    def setUp(self):
        self.pv = pvs.MailboxPV(DBF.LONG, 3, initial=[43], udf=False)
        self.meta = self.pv._MailboxPV__meta
        self.meta.timestamp = (100, 5)

    @inlineCallbacks
    def test_put_int(self):
        R = MockDataRequest()
        
        data = '\1\2' + '\0'*6

        self.pv.put(DBF.SHORT, 1, data, R)
        
        yield R.waiter
        
        self.assertTrue(R.complete)

        self.assertEqual(self.pv.dbf, DBF.LONG)
        self.assertEqual(len(self.pv.value), 1)
        self.assertEqual(self.pv.value[0], 0x102)

    @inlineCallbacks
    def test_put_float(self):
        R = MockDataRequest()
        
        data = 'B(\xcc\xcd' # 42.2

        self.pv.put(DBF.FLOAT, 1, data, R)
        
        yield R.waiter
        
        self.assertTrue(R.complete)

        self.assertEqual(self.pv.dbf, DBF.LONG)
        self.assertEqual(self.pv.value, [42])

    @inlineCallbacks
    def test_put_string(self):
        R = MockDataRequest()
        
        data = '128' + '\0'*37
        assert len(data)==40

        self.pv.put(DBF.STRING, 1, data, R)
        
        yield R.waiter
        
        self.assertTrue(R.complete)

        self.assertEqual(self.pv.dbf, DBF.LONG)
        self.assertEqual(self.pv.value, [128])

    @inlineCallbacks
    def test_put_time(self):
        R = MockDataRequest()

        val = '\1\2' + '\0'*6
        # '!hhIIxx'  sts sevr sec ns pad
        meta = '\0\7' + '\0\2' + '\0\0\7\4' + '\0\0\5\5' + '\0\0'

        data = meta + val

        self.pv.put(DBR.TIME_SHORT, 1, data, R)
        
        yield R.waiter
        
        self.assertTrue(R.complete)

        self.assertEqual(self.pv.dbf, DBF.LONG)
        self.assertEqual(self.pv.value, 0x102)
        self.assertEqual(self.meta.severity, 2)


    def test_get_int(self):
        R = MockDataRequest(dbr=DBR.LONG, dbf=DBF.LONG, dcount=1, metaLen=0)

        self.pv.get(R)
        
        self.assertTrue(hasattr(R,'result'))
        self.assertEqual(R.result, ('\0\0\0\x2b', 1))

    def test_get_float(self):
        R = MockDataRequest(dbr=DBR.FLOAT, dbf=DBF.FLOAT, dcount=1, metaLen=0)

        self.pv.get(R)
        
        self.assertTrue(hasattr(R,'result'))
        self.assertEqual(R.result, ('B,\0\0', 1))

    def test_get_string(self):
        R = MockDataRequest(dbr=DBR.STRING, dbf=DBF.STRING, dcount=1, metaLen=0)

        self.pv.get(R)
        
        self.assertTrue(hasattr(R,'result'))
        self.assertEqual(R.result, ('43'+'\0'*38, 1))

    @inlineCallbacks
    def test_get_time(self):
        dbf, metaLen = dbr_info(DBR.TIME_STRING)
        R = MockDataRequest(dbr=DBR.TIME_STRING, dbf=dbf,
                            dcount=1, metaLen=metaLen,
                            mask=DBE.VALUE)

        self.pv.monitor(R)

        self.assertTrue(hasattr(R,'result'))

        R.reset()

        P = MockDataRequest(dbr=DBR.FLOAT, dbf=DBF.FLOAT, dcount=1, metaLen=0)

        self.assertEqual(self.meta.status, 0)

        self.pv.put(DBR.TIME_FLOAT, 1, '\0\0\0\0\0\1\1\1\0\2\2\2'+'B(\xcc\xcd', P)

        yield P.waiter
        
        self.assertTrue(P.complete)
        self.assertTrue(hasattr(R,'result'))
        
        self.assertEqual(R.result[1], 1)
        res = R.result[0]

        self.assertEqual(res[0:2], '\0\0') # status
        self.assertEqual(res[2:4], '\0\0') # severity
        self.assertEqual(res[4:8], '\0\1\1\1') # sec
        self.assertEqual(res[8:12], '\0\2\2\2') # ns
        self.assertEqual(res[12:], '42' + '\0'*38)
