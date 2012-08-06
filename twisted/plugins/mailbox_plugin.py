# -*- coding: utf-8 -*-

import logging

from zope.interface import implements

from twisted.python import usage, log
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from twisted.application import internet, service

from TwCAS import tcpserver, udpserver
from TwCAS.util import staticserver, mailboxpv

class Options(usage.Options):
    optParameters = [["port", "p", 5064, "CA Server port"],
                     ["pv", '', 'mailbox', "PV Name"]]

class Maker(object):
    implements(IServiceMaker, IPlugin)
    tapname = 'mailbox'
    description = "CA Server with a single PV"
    options = Options

    def makeService(self, options):

        logging.basicConfig(format='%(message)s',
                            level=logging.DEBUG)
        
        server = staticserver.StaticPVServer()
        
        pv = mailboxpv.MailboxPV()
        
        server.add(options['pv']+'.VAL', pv)
        
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

#obs = log.PythonLoggingObserver()
#obs.start()
