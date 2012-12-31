# -*- coding: utf-8 -*-
"""
Bits related to using TwCAS with twisted.application
"""

from TwCAS.protocol.caproto import SharedUDP
from TwCAS.protocol import tcpserver, udpserver

from zope.interface import Interface, Attribute, implements

from TwCAS.util import mailbox, interface

from twisted.plugin import getPlugins, IPlugin
from twisted.application import internet, service

import plugins as _plugins

__all__ = ['SharedUDPServer'
          ,'makeCASService'
          ,'getPVFactory'
          ,'IPVFactory'
          ,'DumbFactory'
          ,'SelfFactory'
          ]

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

class IPVFactory(Interface):
    """Builds a PV using configuration from ConfigParser
    """

    name = Attribute("The unique name this factory is known by")

    def build(config, name):
        """Build a new validator instance.
        
        config - An instance of ConfigParser.SafeConfigParser
        name   - The section name to use for this instance
        
        Returns a instance implementing IDBRPV
        """

class DumbFactory(object):
    """For PV type which need no configuration
    """
    implements(IPVFactory, IPlugin)
    def __init__(self, name, pvclass):
        self.name, self.pvclass = name, pvclass
    def build(self, name, config):
        return self.pvclass()

class SelfFactory(object):
    """For PV types which can configure themselves
    """
    implements(IPVFactory, IPlugin)
    def __init__(self, name, pvclass):
        self.name, self.pvclass = name, pvclass
    def build(self, name, config):
        return self.pvclass(config, name)

class MailboxFactory(object):
    """Makes MailboxPV instances
    """
    implements(IPVFactory, IPlugin)
    name = "Mailbox"
    def build(self, name, config):
        try:
            validator = config.get(name, 'validator')
        except:
            validator = 'default'

        V = None
        for P in getPlugins(interface.IMailboxValidatorFactory, _plugins):
            if P.name == validator:
                V = P.build(name, config)

        if V is None:
            raise KeyError("Could not find validator '%s'"%validator)

        return mailbox.MailboxPV(V)

def getPVFactory(name):
    for P in getPlugins(IPVFactory, _plugins):
        if P.name == name:
            return P
    raise KeyError("Could not find PVFactory '%s'"%name)
