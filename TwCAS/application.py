# -*- coding: utf-8 -*-
"""
Bits related to using TwCAS with twisted.application
"""

from TwCAS.protocol.caproto import SharedUDP
from TwCAS.protocol import tcpserver, udpserver, beacon

from zope.interface import Interface, Attribute, implements

from TwCAS.util import mailbox, interface

from twisted.internet import reactor, defer
from twisted.plugin import getPlugins, IPlugin
from twisted.application import internet, service
from twisted.internet.error import CannotListenError

import plugins as _plugins

__all__ = ['SharedUDPServer'
          ,'getPVFactory'
          ,'IPVFactory'
          ,'DumbFactory'
          ,'SelfFactory'
          ]

class SharedUDPServer(internet.UDPServer):
    """A UDP server using SharedUDP
    """
    def _getPort(self):
        R = getattr(self, 'reactor', reactor)
        port = SharedUDP(reactor=R, *self.args, **self.kwargs)
        port.startListening()
        return port

class CAServerService(service.Service):
    """Handle the ordering when starting CA server parts
    """
    tcpport = None
    udpport = None
    beaconer = None

    def __init__(self, server,
                 tcpport=5064,
                 udpport=5064,
                 beaconport=5065,
                 interface=''):
        self.pvserver = server
        self.tcpnum, self.udpnum  = tcpport, udpport
        self.beaconnum, self.iface = beaconport, interface

    def privilegedStartService(self):
        R = getattr(self, 'reactor', reactor)
        service.Service.privilegedStartService(self)
        
        tcpfact = tcpserver.CASTCPServer(self.pvserver)         
        
        # prefer to start the TCP server on the requested port
        try:
            self.tcpport = R.listenTCP(self.tcpnum,
                                       tcpfact,
                                       interface=self.iface)
        except CannotListenError:
            # fallback to some random port
            self.tcpport = R.listenTCP(0,
                                       tcpfact,
                                       interface=self.iface)
            self.tcpnum = self.tcpport.getHost().port
        
        udpserv = udpserver.CASUDP(self.pvserver, self.tcpnum)

        self.udpport = SharedUDP(self.udpnum,
                                 udpserv,
                                 interface=self.iface,
                                 reactor=R)

        beaconsend = beacon.BeaconProtocol(udpport=self.beaconnum,
                                           tcpport=self.tcpnum,
                                           ifaces=[self.iface],
                                           auto=self.iface==''
                                           )

        self.beaconer = SharedUDP(0,
                                  beaconsend,
                                  interface=self.iface,
                                  reactor=R)

        try:
            self.udpport.startListening()
            self.beaconer.startListening()
        except:
            self.tcpport.stopListening()
            self.udpport.stopListening()
            raise

    def startService(self):
        service.Service.startService(self)
        

    def stopService(self):
        service.Service.stopService(self)
        P = [self.beaconer, self.udpport, self.tcpport]
        P = [p.stopListening() for p in P]
        return defer.DeferredList(P)

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
