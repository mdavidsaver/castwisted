# -*- coding: utf-8 -*-
"""
Created on Sun Jul 29 20:01:56 2012

@author: mdavidsaver
"""

from zope.interface import implements

from twisted.trial import unittest
from twisted.internet.defer import Deferred, inlineCallbacks
from twisted.internet import reactor

from TwCAS.interface import INameServer, IPVServer, IChannel, IPV

from TwCAS import tcpserver, helptest, caproto

from TwCAS.helptest import makeCA, checkCA

class TestPV(object):
    implements(IPV)
    
    def getInfo(self, request):
        return (4, 1, 3)

class TestChannel(object):
    implements(IChannel)
    
    def __init__(self, request):
        self.__proto = request.getCircuit()
        assert self.__proto is not None
        self.pv = request.pv
        self.cid = request.cid
        self.sid = request.sid
        self.client = request.client
        self.clientVersion = request.clientVersion
        
        self.write = self.__proto.transport.write
        
        self.defer = Deferred()
    
    def channelClosed(self):
        D, self.defer = self.defer, None
        D.callback(None)

    def messageReceived(self, cmd, dtype, dcount, p1, p2, payload):
        D, self.defer = self.defer, Deferred()
        D.callback((cmd, dtype, dcount, p1, p2, payload))

    def getCircuit(self):
        return self.__proto

class TestServer(object):
    implements(INameServer, IPVServer)
    
    def __init__(self):
        self.defer=Deferred()
    
    def lookupPV(self, search):
        assert False, 'Never reached'
    
    def connectPV(self, request):
        if request.pv=='iamhere':
            self.defer.callback(request)
        else:
            request.disclaim()

    def buildChannel(self, request, PV):
        return TestChannel(request)

class TestConnect(unittest.TestCase):
    
    timeout = 1.0

    def setUp(self):
        self.nameserv = TestServer()
        self.proto = tcpserver.CASTCP(self.nameserv, prio=6)
        self.transport = helptest.TestTCPTransport()

    def test_version(self):

        @self.transport.defer.addCallback
        def haveVersion(data):
            checkCA(self, data, cmd=0, dtype=6, dcount=caproto.VERSION, p1=0, p2=0)

            self.proto.connectionLost(reason=tcpserver.connectionDone)
            return self.proto.onShutdown

        D = self.transport.defer
        self.proto.makeConnection(self.transport)
        return D

    def test_info(self):
        self.proto.makeConnection(self.transport)

        self.assertEqual(self.proto.prio, 6)
        self.assertEqual(self.proto.peerVersion, 0)
        self.assertEqual(self.proto.peerUser, '<Unknown>')

        msg  = makeCA(0, dtype=42, dcount=caproto.VERSION+1)
        msg += makeCA(20, body=caproto.padMsg('someone'))
        msg += makeCA(21, body=caproto.padMsg('somewhere'))

        self.proto.dataReceived(msg)

        self.assertEqual(self.proto.prio, 42)
        self.assertEqual(self.proto.peerVersion, caproto.VERSION+1)
        self.assertEqual(self.proto.peerUser, 'someone')

class TestCASChannel(unittest.TestCase):
    
    timeout = 1.0

    def setUp(self):
        self.serv = TestServer()
        self.proto = tcpserver.CASTCP(self.serv, prio=6)
        self.transport = helptest.TestTCPTransport()
        self.proto.makeConnection(self.transport)

        self.proto.peerVersion = caproto.VERSION+1
        self.proto.peerUser = 'someone'

    @inlineCallbacks
    def test_create(self):
        msg = makeCA(18, p1=15, p2=caproto.VERSION, body=caproto.padMsg('iamhere'))

        self.proto.dataReceived(msg)

        request = yield self.serv.defer

        self.assertEqual(request.pv, 'iamhere')
        self.assertEqual(request.cid, 15)
        self.assertEqual(request.sid, 0)
        self.assertEqual(request.client, ('127.0.0.2', 4231))
        self.assertEqual(request.clientVersion, caproto.VERSION+1)

        D = Deferred()
        reactor.callLater(0.1, D.callback, request)

        request = yield D
        
        D = self.transport.defer

        chan = request.claim(TestPV())
            
        self.assertEqual(self.proto._CASTCP__channels[chan.sid], chan)
            
        self.assertEqual(chan.pv, 'iamhere')
        self.assertEqual(chan.cid, 15)
        self.assertEqual(chan.client, ('127.0.0.2', 4231))
        self.assertEqual(chan.clientVersion, caproto.VERSION+1)
            
        data = yield D

        pkt, rem = checkCA(self, data, cmd=22, p1=15, p2=3)
        pkt, rem = checkCA(self, rem, cmd=18, dtype=4, dcount=1, p1=15, p2=0)
        
        D = self.transport.defer
            
        msg = makeCA(12, p1=chan.sid, p2=chan.cid)
        self.proto.dataReceived(msg)
        
        data = yield D

        checkCA(self, data, cmd=12, p1=chan.sid, p2=chan.cid, final=True)
        
        self.assertTrue(chan.sid not in self.proto._CASTCP__channels)

    @inlineCallbacks
    def test_nochan(self):
        msg = makeCA(18, p1=15, p2=caproto.VERSION, body=caproto.padMsg('iamnot'))
    
        D = self.transport.defer
        
        self.proto.dataReceived(msg)
        
        data = yield D
        
        checkCA(self, data, cmd=26, p1=15, final=True)

    @inlineCallbacks
    def test_chanforward(self):
        msg = makeCA(18, p1=15, p2=caproto.VERSION, body=caproto.padMsg('iamhere'))

        self.proto.dataReceived(msg)

        request = yield self.serv.defer
        
        chan = request.claim(TestPV())

        D = chan.defer

        msg = makeCA(cmd=15, dtype=4, dcount=1, p1=chan.sid, p2=5678)
        self.proto.dataReceived(msg)

        cmd, dtype, dcount, p1, p2, payload = yield D

        self.assertEqual(cmd, 15)
        self.assertEqual(dtype, 4)
        self.assertEqual(dcount, 1)
        self.assertEqual(p1, chan.sid)
        self.assertEqual(p2, 5678)
