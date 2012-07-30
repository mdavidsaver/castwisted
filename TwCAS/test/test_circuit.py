# -*- coding: utf-8 -*-
"""
Created on Sun Jul 29 20:01:56 2012

@author: mdavidsaver
"""

from zope.interface import implements

from twisted.trial import unittest
from twisted.internet.defer import Deferred

from TwCAS.interface import INameServer, IPVServer

from TwCAS import tcpserver, helptest, caproto

from TwCAS.helptest import makeCA, checkCA

class TestServer(object):
    implements(INameServer, IPVServer)
    
    def __init__(self):
        self.defer=Deferred()
    
    def lookupPV(self, search):
        self.defer.callback(search)

    def buildChannel(request, PV):
        pass

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
