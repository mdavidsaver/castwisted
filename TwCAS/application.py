# -*- coding: utf-8 -*-
"""
Bits related to using TwCAS with twisted.application
"""

from TwCAS.caproto import SharedUDP
from TwCAS import tcpserver, udpserver

from TwCAS.util import pvs, mailbox, interface

from twisted.plugin import getPlugins
from twisted.application import internet, service

__all__ = ['SharedUDPServer','makeCASService','getPVFactory']

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

def mailboxFactory(name, config):
    try:
        validator = config.get(name, 'validator')
    except:
        validator = 'default'

    possible = getPlugins(interface.IMailbox)
    
    for P in possible:
        if P.__class__.__name__==validator:
            val = P(config, name)
            return mailbox.MailboxPV(val)

    raise KeyError("%s: validator '%s' not found"%(name, validator))

def _makeNullFactory(cls):
    def factory(name, config):
        return cls()
    return factory

_pv_types = {
    'Mailbox':mailboxFactory,
    'Spam':_makeNullFactory(pvs.Spam),
    'ClientInfo':_makeNullFactory(pvs.ClientInfo),
    'Mutex':_makeNullFactory(pvs.Mutex),
}

def getPVFactory(name):
    return _pv_types[name]
