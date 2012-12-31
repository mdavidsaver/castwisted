# -*- coding: utf-8 -*-

from zope.interface import implements

from twisted.trial import unittest
from twisted.internet.defer import Deferred, inlineCallbacks

from TwCAS.protocol.interface import IPVRequest, IPVDBR

from TwCAS.protocol import channel as chan

from TwCAS.protocol import helptest, ECA

class MockCircuit(object):
    paused = False
    dropped = None
    def __init__(self):
        self.transport = helptest.TestTCPTransport()

    def dropChannel(self, chan):
        self.dropped = chan

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
    
    def put(dtype, dcount, dbrdata, reply=None, chan=None):
        pass
    
    def get(self, request):
        pass
    
    def monitor(self, request):
        pass

class TestLifecycle(unittest.TestCase):

    timeout = 1.0

    def setUp(self):
        self.pv = MockPV()
        self.request = MockRequest(pv=self.pv, sid=5, cid=17,
                                   client=('127.0.0.2', 4231),
                                   clientVersion=10, clientUser='someone')
        self.transport = self.request.getCircuit()

    

    def test_openclose(self):
        C = chan.Channel(self.request, self.pv)

        C.channelClosed()

    @inlineCallbacks
    def test_forceclose(self):
        C = chan.Channel(self.request, self.pv)
        
        D = self.transport.defer
        
        C.close()
        
        self.assertIdentical(C, self.request._circuit.dropped)

        data = yield D
        
        helptest.checkCA(self, data, cmd=27, dtype=0, dcount=0,
                         p1=self.request.cid, p2=0, bodylen=0,
                         final=True)

class TestOperations(unittest.TestCase):

    timeout = 1.0

    def setUp(self):
        self.pv = MockPV()
        self.request = MockRequest(pv=self.pv, sid=5, cid=17,
                                   client=('127.0.0.2', 4231),
                                   clientVersion=10, clientUser='someone')
        self.chan = chan.Channel(self.request, self.pv)
        self.transport = self.request.getCircuit()

    def tearDown(self):
        self.chan.channelClosed()

    @inlineCallbacks
    def test_getnotify(self):
        D = Deferred()
        
        self.pv.get = D.callback
        
        self.chan.messageReceived(cmd=15, dtype=1, dcount=1,
                                  p1=self.request.sid, p2=10000,
                                  payload='')
        
        get = yield D

        self.assertIdentical(get.channel, self.chan)

        D = self.transport.defer
        self.transport.transport.rxneeded = 2 # header and body send with seperate write() calls
        
        self.assertTrue(get.updateDBR('\0'*8, 1))

        msg = yield D

        helptest.checkCA(self, msg, cmd=15, dtype=1, dcount=1,
                         p1=ECA.ECA_NORMAL, p2=10000,
                         body='\0'*8, bodylen=8, hasdbr=True, final=True)

        self.assertTrue(get.complete)

    @inlineCallbacks
    def test_putnotify(self):
        D = Deferred()
        
        self.pv.put = lambda v,w,x,y,z:D.callback((v,w,x,y,z))

        self.chan.messageReceived(cmd=19, dtype=0, dcount=1,
                                  p1=self.request.sid, p2=10000,
                                  payload='a'*8)

        dtype, dcount, data, put, chan = yield D

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
        
        self.pv.put = lambda v,w,x,y,z:D.callback((v,w,x,y,z))

        self.chan.messageReceived(cmd=4, dtype=0, dcount=1,
                                  p1=self.request.sid, p2=10000,
                                  payload='a'*8)

        dtype, dcount, data, put, chan = yield D

        self.assertEqual(dtype, 0)
        self.assertEqual(dcount, 1)
        self.assertEqual(data, 'a'*8)
        self.assertIdentical(put, None)

    @inlineCallbacks
    def test_monitor(self):
        D = Deferred()
        
        self.pv.monitor = D.callback

        self.chan.messageReceived(cmd=1, dtype=1, dcount=1,
                                  p1=self.request.sid, p2=10000,
                                  payload='\0'*12+'\0\3\0\0')

        monitor = yield D
        
        self.assertIdentical(monitor.channel, self.chan)
        self.assertEqual(monitor.mask, 3)

        for I in range(5):
            D = self.transport.defer
            self.transport.transport.rxneeded = 2

            monitor.updateDBR('\0'*7+chr(I), 1)

            data = yield D

            pkt,_ = helptest.checkCA(self, data, cmd=1, dtype=1, dcount=1,
                                     p1=ECA.ECA_NORMAL, p2=10000,
                                     bodylen=8, hasdbr=True, final=True)

            self.assertEqual(str(pkt.body), '\0'*7+chr(I))

        D = self.transport.defer
        self.transport.transport.rxneeded = 1

        self.chan.messageReceived(cmd=2, dtype=1, dcount=1,
                                  p1=self.request.sid, p2=10000,
                                  payload='')

        data = yield D

        helptest.checkCA(self, data, cmd=1, dtype=1, dcount=1,
                         p1=self.request.sid, p2=10000, final=True)

        self.assertEqual(self.chan._Channel__subscriptions, {})

class TestShutdown(unittest.TestCase):
    """Ensure the in progress operations are aborted
    when the channel is closed.
    """

    timeout = 1.0

    def setUp(self):
        self.pv = MockPV()
        self.request = MockRequest(pv=self.pv, sid=5, cid=17,
                                   client=('127.0.0.2', 4231),
                                   clientVersion=10, clientUser='someone')
        self.chan = chan.Channel(self.request, self.pv)
        self.transport = self.request.getCircuit()

    @inlineCallbacks
    def test_monitor(self):
        D = Deferred()
        
        self.pv.monitor = D.callback

        self.chan.messageReceived(cmd=1, dtype=0, dcount=1,
                                  p1=self.request.sid, p2=10000,
                                  payload='\0'*12+'\0\3\0\0')

        monitor = yield D

        self.assertFalse(monitor.complete)
        
        self.chan.close()
        
        self.assertTrue(monitor.complete)
        
        self.assertFalse(monitor.updateDBR('\0'*8, 1))

        self.assertEqual(self.chan._Channel__subscriptions, {})

    @inlineCallbacks
    def test_get(self):
        D = Deferred()
        
        self.pv.get = D.callback
        
        self.chan.messageReceived(cmd=15, dtype=0, dcount=1,
                                  p1=self.request.sid, p2=10000,
                                  payload='')
        
        get = yield D

        self.assertFalse(get.complete)
        
        self.chan.close()
        
        self.assertTrue(get.complete)
        
        self.assertFalse(get.updateDBR('\0'*8, 1))

    @inlineCallbacks
    def test_put(self):
        D = Deferred()
        
        self.pv.put = lambda v,w,x,y,z:D.callback((v,w,x,y,z))

        self.chan.messageReceived(cmd=19, dtype=0, dcount=1,
                                  p1=self.request.sid, p2=10000,
                                  payload='a'*8)

        dtype, dcount, data, put, chan = yield D

        self.assertFalse(put.complete)
        
        self.chan.close()
        
        self.assertTrue(put.complete)
        
        self.assertFalse(put.finish())
