# -*- coding: utf-8 -*-
"""
Created on Sun Jul 29 11:54:16 2012

@author: mdavidsaver
"""

from zope.interface import implements

from TwCAS import udpserver
from TwCAS import helptest
from TwCAS.caproto import VERSION, padMsg
from TwCAS.interface import INameServer

from twisted.internet.defer import Deferred
from twisted.trial import unittest
from twisted.python.failure import Failure

import struct

class TestNameServer(object):
    implements(INameServer)
    
    def __init__(self):
        self.defer=Deferred()
    
    def lookupPV(self, search):
        self.defer.callback(search)
    

class TestUDP(unittest.TestCase):
    
    timeout = 1.0    
    
    def setUp(self):
        self.nameserv = TestNameServer()
        self.proto = udpserver.CASUDP(self.nameserv, 1433)
        self.transport = helptest.TestUDPTransport()
        self.proto.makeConnection(self.transport)

    def test_lookuplocal(self):
        client = ('127.0.0.1',1234)

        @self.nameserv.defer.addBoth
        def checkSearch(result):
            if isinstance(result, Failure):
                self.fail('timeout waiting for search results. '+str(result))
                return
            self.assertEqual(result.pv, 'helloworld')
            self.assertEqual(result.cid, 4242)
            self.assertEqual(result.client, client)
            self.assertEqual(result.clientVersion, 10)
            result.claim()
            return self.transport.defer

        @self.transport.defer.addBoth
        def checkReply(result):
            if isinstance(result, Failure):
                self.fail('timeout waiting for search reply. '+str(result))
                return
            pkt, dest = result
            self.assertEqual(dest, client)
            ebody = struct.pack('!Hxxxxxx', VERSION)
            msg, remainder = helptest.checkCA(self, pkt, cmd=6, bodylen=8,
                                              dtype=1433, dcount=0, p1=0xffffffff,
                                              p2=4242, body=ebody)

            self.assertEqual(str(remainder), '')

        request  = helptest.makeCA(0, dtype=15, dcount=10)
        request += helptest.makeCA(6, dtype=5, dcount=10, p1=4242, p2=4242,
                                   body=padMsg('helloworld'))

        self.proto.datagramReceived(request, client)

        return self.nameserv.defer

    def test_lookupNameServer(self):
        client = ('127.0.0.1',1234)
        server = ('192.168.5.1', 4321)

        @self.nameserv.defer.addCallback
        def checkSearch(result):
            self.assertEqual(result.pv, 'helloworld')
            self.assertEqual(result.cid, 4242)
            self.assertEqual(result.client, client)
            self.assertEqual(result.clientVersion, 10)
            result.claim(server=server)
            return self.transport.defer

        @self.transport.defer.addCallback
        def checkReply(result):
            pkt, dest = result
            self.assertEqual(dest, client)
            ebody = struct.pack('!Hxxxxxx', VERSION)
            msg, remainder = helptest.checkCA(self, pkt, cmd=6, bodylen=8,
                                              dtype=4321, dcount=0, p1=0xc0a80501,
                                              p2=4242, body=ebody)

            self.assertEqual(str(remainder), '')
            return result

        request  = helptest.makeCA(0, dtype=15, dcount=10)
        request += helptest.makeCA(6, dtype=5, dcount=10, p1=4242, p2=4242,
                                  body=padMsg('helloworld'))

        self.proto.datagramReceived(request, client)
        

        return self.nameserv.defer
