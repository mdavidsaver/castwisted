# -*- coding: utf-8 -*-

import logging

from zope.interface import implements

from twisted.python import usage, log
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker

from TwCAS.application import makeCASService
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
    tapname = 'pvdemo'
    description = "CA Server with a demo PVs"
    options = Options

    def makeService(self, options):
        
        server = staticserver.StaticPVServer()
        
        prefix = options['prefix']
        
        pv = pvs.DynamicMailboxPV(maxCount=int(options['count']))
        server.add(prefix+'mailbox.VAL', pv)
        
        pv = pvs.ClientInfo()
        server.add(prefix+'whoami.VAL', pv)
        
        pv = pvs.Spam()
        server.add(prefix+'spam.VAL', pv)
        
        port = int(options['port'])

        return makeCASService(server, port)

serviceMaker = Maker()
