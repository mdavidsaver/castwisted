# -*- coding: utf-8 -*-

from twisted.trial import unittest
from twisted.internet.protocol import Protocol
from twisted.internet.defer import Deferred, DeferredList, inlineCallbacks

from TwCAS import pair

class PP(Protocol):
    connected=False
    def __init__(self):
        self.recv = ''
    def connectionMade(self):
        self.connected=True
    def dataReceived(self, data):
        self.recv += data

class TestConnectPair(unittest.TestCase):

    @inlineCallbacks
    def test_makepair(self):
        A, B = yield pair.makePair(PP)

        dA, dB = Deferred(), Deferred()
        
        A.connectionLost = dA.callback
        B.connectionLost = dB.callback

        A.transport.loseConnection()
        B.transport.loseConnection()

        yield DeferredList([dA, dB])

class TestDataPair(unittest.TestCase):

    @inlineCallbacks
    def setUp(self):
        self.A, self.B = yield pair.makePair(PP)

    @inlineCallbacks
    def tearDown(self):
        dA, dB = Deferred(), Deferred()
        self.A.connectionLost = dA.callback
        self.B.connectionLost = dB.callback
        self.A.transport.loseConnection()
        self.B.transport.loseConnection()
        yield DeferredList([dA, dB])

    @inlineCallbacks
    def test_senda(self):
        rx = Deferred()
        self.B.dataReceived = rx.callback

        self.A.transport.write('hello')
        
        data = yield rx

        self.assertEqual(data, 'hello')

    @inlineCallbacks
    def test_sendb(self):
        rx = Deferred()
        self.A.dataReceived = rx.callback

        self.B.transport.write('hello')
        
        data = yield rx

        self.assertEqual(data, 'hello')

