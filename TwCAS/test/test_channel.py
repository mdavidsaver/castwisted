# -*- coding: utf-8 -*-

from zope.interface import implements

from twisted.trial import unittest
from twisted.internet.defer import Deferred, inlineCallbacks

from TwCAS.interface import IPVRequest, IPVDBR

from TwCAS import channel as chan

from TwCAS import helptest, caproto, ECA

class MockCircuit(object):
    paused = False
    def __init__(self):
        self.transport = helptest.TestTCPTransport()

    @property
    def defer(self):
        return self.transport.defer

    @property
    def pmux(self):
        return self.transport

class MockRequest(object):
    implements(IPVRequest)
    
    def __init__(self, **kws):
        self._circuit = MockCircuit()
        self.replied = False
        for k,v in kws.iteritems():
            setattr(self, k, v)

    def getCircuit(self):
        return self._circuit

class MockPV(object):
    implements(IPVDBR)
    
    def getInfo(self, request):
        return (0, 1, 3)
    
    def put(dtype, dcount, dbrdata, reply=None):
        pass
    
    def get(self, request):
        pass
    
    def monitor(self, request):
        pass

class TestLifecycle(unittest.TestCase):

    def setUp(self):
        self.request = MockRequest(pv='hello', sid=5, cid=17,
                                   client=('127.0.0.2', 4231),
                                   clientVersion=10)

        self.pv = MockPV()
    

    def test_openclose(self):
        C = chan.Channel(self.request, self.pv)

        C.channelClosed()

class TestGet(unittest.TestCase):

    timeout = 1.0

    def setUp(self):

        self.pv = MockPV()
        self.request = MockRequest(pv=self.pv, sid=5, cid=17,
                                   client=('127.0.0.2', 4231),
                                   clientVersion=10)
        self.chan = chan.Channel(self.request, self.pv)
        self.transport = self.request.getCircuit()

    def tearDown(self):
        self.chan.channelClosed()

    @inlineCallbacks
    def test_getnotify(self):
        D = Deferred()
        
        self.pv.get = D.callback
        
        self.chan.messageReceived(cmd=15, dtype=0, dcount=1,
                                  p1=self.request.sid, p2=10000,
                                  payload='')
        
        get = yield D

        self.assertIdentical(get.channel, self.chan)

        D = self.transport.defer
        self.transport.transport.rxneeded = 2 # header and body send with seperate write() calls
        
        self.assertTrue(get.update('\0'*8, 1))

        msg = yield D

        helptest.checkCA(self, msg, cmd=15, dtype=0, dcount=1,
                         p1=ECA.ECA_NORMAL, p2=10000,
                         body='\0'*8, bodylen=8, hasdbr=True, final=True)

        self.assertTrue(get.complete)

    @inlineCallbacks
    def test_putnotify(self):
        D = Deferred()
        
        self.pv.put = lambda w,x,y,z:D.callback((w,x,y,z))

        self.chan.messageReceived(cmd=19, dtype=0, dcount=1,
                                  p1=self.request.sid, p2=10000,
                                  payload='a'*8)

        dtype, dcount, data, put = yield D

        self.assertEqual(dtype, 0)
        self.assertEqual(dcount, 1)
        self.assertEqual(data, 'a'*8)
        self.assertIdentical(put.channel, self.chan)

        D = self.transport.defer
        
        self.assertTrue(put.finish())

        msg = yield D

        helptest.checkCA(self, msg, cmd=19, dtype=0, dcount=1,
                         p1=ECA.ECA_NORMAL, p2=10000)

    @inlineCallbacks
    def test_put(self):
        D = Deferred()
        
        self.pv.put = lambda w,x,y,z:D.callback((w,x,y,z))

        self.chan.messageReceived(cmd=4, dtype=0, dcount=1,
                                  p1=self.request.sid, p2=10000,
                                  payload='a'*8)

        dtype, dcount, data, put = yield D

        self.assertEqual(dtype, 0)
        self.assertEqual(dcount, 1)
        self.assertEqual(data, 'a'*8)
        self.assertIdentical(put, None)

    @inlineCallbacks
    def test_monitor(self):
        D = Deferred()
        
        self.pv.monitor = D.callback

        self.chan.messageReceived(cmd=1, dtype=0, dcount=1,
                                  p1=self.request.sid, p2=10000,
                                  payload='\0'*12+'\0\3\0\0')

        monitor = yield D
        
        self.assertIdentical(monitor.channel, self.chan)
        self.assertEqual(monitor.mask, 3)

        for I in range(5):
            D = self.transport.defer
            self.transport.transport.rxneeded = 2

            monitor.update('\0'*7+chr(I), 1)

            data = yield D

            pkt,_ = helptest.checkCA(self, data, cmd=1, dtype=0, dcount=1,
                                     p1=ECA.ECA_NORMAL, p2=10000,
                                     bodylen=8, hasdbr=True, final=True)

            self.assertEqual(str(pkt.body), '\0'*7+chr(I))

        D = self.transport.defer
        self.transport.transport.rxneeded = 1

        self.chan.messageReceived(cmd=2, dtype=0, dcount=1,
                                  p1=self.request.sid, p2=10000,
                                  payload='')

        data = yield D

        helptest.checkCA(self, data, cmd=1, dtype=0, dcount=1,
                         p1=self.request.sid, p2=10000, final=True)
