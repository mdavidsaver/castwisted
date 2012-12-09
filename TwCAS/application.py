# -*- coding: utf-8 -*-
"""
Bits related to using TwCAS with twisted.application
"""

from TwCAS.caproto import SharedUDP
from TwCAS import tcpserver, udpserver

from twisted.application import internet, service

__all__ = ['SharedUDPServer','makeCASService']

class SharedUDPServer(internet.UDPServer):
    """A UDP server using SharedUDP
    """
    def _getPort(self):
        if self.reactor is None:
            from twisted.internet import reactor
        else:
            reactor = self.reactor
        port = SharedUDP(reactor=reactor, *self.args, **self.kwargs)
        port.startListening()
        return port

def makeCASService(server, port=5064, interface=''):
    """Builds a Twisted Service (is there really any other kind?)
    
    server - Should implement INameServer and IPVServer
    """
    fact = tcpserver.CASTCPServer(port, server)   

    tcpserv = internet.TCPServer(port, fact,
                                 interface=interface)

    udpserv = SharedUDPServer(port,
                                 udpserver.CASUDP(server, port),
                                 interface=interface)

    caserver = service.MultiService()
    tcpserv.setServiceParent(caserver)
    udpserv.setServiceParent(caserver)
    
    return caserver
