# -*- coding: utf-8 -*-

from twisted.trial import unittest
from twisted.internet.protocol import Protocol
from twisted.internet.defer import Deferred, inlineCallbacks

from TwCAS.protocol import pair

class PP(Protocol):
    connected=False
    def __init__(self):
        self.recv = ''
    def connectionMade(self):
        self.connected=True
    def connectionLost(self):
        self.connected=False
    def dataReceived(self, data):
        self.recv += data

class TestConnectPair(unittest.TestCase):

    timeout = 1.0

    @inlineCallbacks
    def test_makepair(self):
        A, B = yield pair.makePair(PP)
        
        yield pair.closeAll([A,B], close=True)

class TestDataPair(unittest.TestCase):

    timeout = 1.0
    
    @inlineCallbacks
    def setUp(self):
        self.A, self.B = yield pair.makePair(PP)

    def tearDown(self):
        return pair.closeAll([self.A, self.B], close=True)

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

