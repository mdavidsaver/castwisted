# -*- coding: utf-8 -*-
"""
Created on Sun Aug  5 09:59:58 2012

@author: -
"""

from twisted.internet import reactor
from twisted.internet.defer import Deferred, DeferredList, inlineCallbacks, returnValue

from twisted.internet.protocol import ServerFactory, ClientFactory

__all__ = ['makePair']

class PairServerFactory(ServerFactory):
    def __init__(self, protocol, reactor=reactor):
        self.protocol = protocol
        self._L = reactor.listenTCP(0, self, backlog=1,
                                    interface='127.0.0.1')

        self.defer = Deferred(self.done)
        self.port = self._L.getHost().port
    def buildProtocol(self, addr):
        P = self.protocol()
        CM = P.connectionMade
        def announceConnect():
            CM()
            self.defer.callback(P)
        P.connectionMade = announceConnect
        return P
    def done(self):
        self._L.stopListening()

class PairClientFactory(ClientFactory):
    def __init__(self, protocol, port, reactor=reactor):
        self.protocol = protocol
        self._C = reactor.connectTCP('127.0.0.1', port, self, timeout=1)
        self.defer = Deferred(self._C.stopConnecting)
    def buildProtocol(self, addr):
        P = self.protocol()
        CM = P.connectionMade
        def announceConnect():
            CM()
            self.defer.callback(P)
        P.connectionMade = announceConnect
        return P

@inlineCallbacks
def makePair(protoA, protoB=None, reactor=reactor):
    """Build a stream connection using the given protocol(s).
    
    Returns a tuple (A,B) where A and B are instances of the
    given protocol(s).
    
    It is guaranteed that connectionMade will have been called
    for both instances before this function returns.

    """
    if protoB is None:
        protoB=protoA
    SF = PairServerFactory(protoA, reactor=reactor)
    CF = PairClientFactory(protoB, SF.port, reactor=reactor)
    
    L = DeferredList([SF.defer, CF.defer])
    [(sA,A), (sB,B)] = yield L

    SF.done()
    
    returnValue((A,B))
