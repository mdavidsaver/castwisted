# -*- coding: utf-8 -*-

import weakref
import logging

logging.basicConfig(level=logging.ERROR)

from twisted.trial import unittest

from twisted.internet import reactor
from twisted.internet.defer import Deferred, inlineCallbacks

from TwCAS.util import mailbox, pvs
from TwCAS import ECA
from TwCAS.dbr import DBF, DBR, DBE, dbr_info

class NullValidator(object):
    def __init__(self, dbf, maxCount, initial):
        self.maxCount = maxCount
        self.nativeDBF = self.putDBF = dbf
        self.rights = 3
        self.IV = initial
    def setup(self):
        return (self.nativeDBF, self.IV, None)
    def put(self,(dbf, value, meta), reply=None, chan=None):
        return (dbf, value, meta)

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
    def updateDBR(self, data, dcount, eca=None):
        self.result = (data, dcount)
        self.eca = eca
        self.waiter.callback(eca==ECA.ECA_NORMAL)
    def finish(self):
        self.error(ECA.ECA_NORMAL)

class TestNumeric(unittest.TestCase):
    timeout = 1
    
    def setUp(self):
        self.valid = NullValidator(DBF.LONG, 3, [43])
        self.pv = mailbox.MailboxPV(self.valid)
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

        self.assertEqual(R.eca, None)
        self.assertTrue(hasattr(R,'result'))
        self.assertEqual(R.result, ('B,\0\0', 1))

    def test_get_string(self):
        R = MockDataRequest(dbr=DBR.STRING, dbf=DBF.STRING, dcount=1, metaLen=0)

        self.pv.get(R)

        self.assertTrue(hasattr(R,'result'))
        self.assertEqual(R.result, ('43'+'\0'*38, 1))

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
        
        @P.waiter.addCallback
        def finish(_):
            self.assertTrue(P.complete)
            self.assertTrue(hasattr(R,'result'))
            
            self.assertEqual(R.result[1], 1)
            res = R.result[0]
    
            self.assertEqual(res[0:2], '\0\0') # status
            self.assertEqual(res[2:4], '\0\0') # severity
            self.assertEqual(res[4:8], '\0\1\1\1') # sec
            self.assertEqual(res[8:12], '\0\2\2\2') # ns
            self.assertEqual(res[12:], '42' + '\0'*38)
    
            self.assertEqual(1, len(self.pv._MailboxPV__subscriptions))
    
            # Now we want to check that MailboxPV "forgets" about
            # monitors which are no longer referenced by a source.
            # Since weakref is used internall this is really
            # a check that MailboxPV doesn't hold any other refs.
            #
            # Now we play some games to ensure that no refs
            # remain when we do this test.
            # (this is needed in python 2.6.6)
    
            D = Deferred()
            D.addCallback(lambda x:None)
            reactor.callLater(0, self.check_cleanup, D, weakref.ref(R))
            return D

        return P.waiter

    def check_cleanup(self, D, ref):
        D.callback(None)
        del D

        import gc
        gc.collect()
        self.assertTrue(ref() is None)
        self.assertEqual(0, len(self.pv._MailboxPV__subscriptions))

