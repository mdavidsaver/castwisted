# -*- coding: utf-8 -*-

import logging

from zope.interface import implements

from twisted.python import usage, log
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from twisted.application import internet, service

from TwCAS import tcpserver, udpserver
from TwCAS.util import staticserver, pvs

class TwistedLogAdapter(logging.Handler):
    def emit(self, record):
        log.msg(self.format(record))

H = TwistedLogAdapter()

L = logging.getLogger()
L.setLevel(logging.DEBUG)
L.addHandler(H)
                            
class Options(usage.Options):
    optParameters = [["port", "p", 5064, "CA Server port"],
                     ["prefix", 'P', '', "PV Name prefix"],
                     ["count", "c", 1, "Max element count"]
                    ]

class Maker(object):
    implements(IServiceMaker, IPlugin)
    tapname = 'mailbox'
    description = "CA Server with a single PV"
    options = Options

    def makeService(self, options):
        
        server = staticserver.StaticPVServer()
        
        prefix = options['prefix']
        
        pv = pvs.MailboxPV(maxCount=int(options['count']))
        server.add(prefix+'mailbox.VAL', pv)
        
        pv = pvs.ClientInfo()
        server.add(prefix+'whoami.VAL', pv)
        
        pv = pvs.Spam()
        server.add(prefix+'spam.VAL', pv)
        
        port = int(options['port'])
        
        fact = tcpserver.CASTCPServer(port, server)        
        
        tcpserv = internet.TCPServer(port, fact)

        udpserv = internet.UDPServer(port,
                                     udpserver.CASUDP(server, port))

        caserver = service.MultiService()
        tcpserv.setServiceParent(caserver)
        udpserv.setServiceParent(caserver)
        
        return caserver

serviceMaker = Maker()
