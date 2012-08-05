# -*- coding: utf-8 -*-

from zope.interface import implements

from twisted.trial import unittest

from twisted.internet.interfaces import IConsumer, IPushProducer
from twisted.internet.protocol import Protocol
from twisted.internet.defer import Deferred, inlineCallbacks
from twisted.internet import error

from TwCAS.PMux import MuxProducer
from TwCAS import pair

class MockConsumer(object):
    implements(IConsumer)
    tripnext=False
    def registerProducer(self, producer, streaming):
        self.producer=producer
    def unregisterProducer(self):
        self.producer=None
    def write(self, data):
        if self.tripnext:
            self.producer.pauseProducing()

class MockPushProducer(object):
    implements(IPushProducer)
    running = None
    def resumeProducing(self):
        self.running = True
    def pauseProducing(self):
        self.running = False
    def stopProducing(self):
        self.running = None

class TestMux(unittest.TestCase):

    timeout = 1.0

    def setUp(self):
        self.cons = MockConsumer()
        self.prod = MuxProducer(self.cons)

    def test_one(self):
        P = MockPushProducer()
        C = self.prod.getConsumer()
        C.registerProducer(P, True)

        self.assertEqual(self.prod._consumers, [C])

        self.prod.pauseProducing()

        self.assertTrue(P.running is False)

        self.prod.resumeProducing()

        self.assertTrue(P.running is True)

        self.prod.stopProducing()

        self.assertTrue(P.running is None)

        C.unregisterProducer()

        self.assertEqual(self.prod._consumers, [])

    def test_many(self):
        Ps = []
        Cs = []
        for n in range(5):
            P = MockPushProducer()
            C = self.prod.getConsumer()
            C.registerProducer(P, True)
            Ps.append(P)
            Cs.append(C)

        self.assertEqual(self.prod._consumers, Cs)

        self.prod.pauseProducing()

        [self.assertTrue(P.running is False) for P in Ps]

        P0 = Ps.pop(0)
        C0 = Cs.pop(0)
        C0.unregisterProducer()

        self.assertEqual(self.prod._consumers, Cs)

        self.prod.resumeProducing()

        [self.assertTrue(P.running is True) for P in Ps]
        self.assertTrue(P0.running is False)

        self.prod.stopProducing()

        [self.assertTrue(P.running is None) for P in Ps]

        [C.unregisterProducer() for C in Cs]

        self.assertEqual(self.prod._consumers, [])

    @inlineCallbacks
    def test_waiter(self):
        W = self.prod.getWaiter()
        self.assertEqual(self.prod._waiters, []) # already fired

        self.assertTrue(W.called)

        self.prod.pauseProducing()
        self.assertTrue(self.prod._paused)

        W = self.prod.getWaiter()
        self.assertEqual(self.prod._waiters, [W])
        self.assertFalse(W.called)

        self.prod.resumeProducing()
        self.assertEqual(self.prod._waiters, [])

        self.assertTrue(W.called)

        self.prod.pauseProducing()

        W = self.prod.getWaiter()

        self.assertEqual(self.prod._waiters, [W])
        self.assertFalse(W.called)

        self.prod.stopProducing()

        self.assertEqual(self.prod._waiters, [])
        self.assertTrue(W.called)

        try:
            R = yield W
            print 'R',R
            self.assertTrue(False, 'Did not get expected exception')
        except error.ConnectionDone:
            self.assertTrue(True)

class TestLimit(unittest.TestCase):

    timeout = 1.0

    @inlineCallbacks
    def setUp(self):
        self.EP = yield pair.makePair(Protocol)

    def tearDown(self):
        return pair.closeAll(self.EP, close=True)

    @inlineCallbacks
    def test_hold(self):
        """ Test that our producer will get notification
        when the socket buffer is full.

        This is a test of my understanding of how the twisted core behaves
        """
        Dresume = Deferred()
        P = MockPushProducer()
        Prev = P.resumeProducing
        P.resumeProducing = lambda:Dresume.callback(Prev())
        P.running = True

        T = self.EP[0].transport
        T.registerProducer(P, True)

        R = self.EP[1]

        Ddata = Deferred()
        R.expect = 0
        R.rbuf = ''
        def onRx(data):
            R.rbuf += data
            if len(R.rbuf)>R.expect:
                Ddata.errback('More data %d than expected %d'%(len(R.rbuf),R.expect))
            elif len(R.rbuf)==R.expect:
                Ddata.callback(R.rbuf)
        R.dataReceived = onRx

        bmax = T.bufferSize
        bchunk = max(1, bmax/4) + 5 # always sends a little more than bufferSize

        self.assertTrue(P.running)

        # keep sending until notified that the buffer is full
        while P.running:
            T.write('\0'*bchunk)
            R.expect+=bchunk

        self.assertTrue(R.expect > 0)
        self.assertFalse(P.running)

        yield Dresume

        self.assertTrue(P.running)

        yield Ddata
