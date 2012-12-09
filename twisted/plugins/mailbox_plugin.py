# -*- coding: utf-8 -*-

import logging

from zope.interface import implements

from twisted.python import usage, log
from twisted.plugin import IPlugin
from twisted.application import service

from TwCAS.application import makeCASService
from TwCAS.util import staticserver, mailbox
from TwCAS.dbr.defs import string2DBF, DBR

class TwistedLogAdapter(logging.Handler):
    def emit(self, record):
        log.msg(self.format(record))

H = TwistedLogAdapter()

L = logging.getLogger()
L.setLevel(logging.DEBUG)
L.addHandler(H)


class Options(usage.Options):
    optParameters = [["ip", "", "127.0.0.1", "Address of interface"],
                     ["port", "", "5064", "CA Server port"],
                     ["pv", "n", "testPV", "PV Name"],
                     ["dbf","t", "STRING", "DBF type"],
                     ["maxcount","m", "1", "Max value count"],
                     ["initial","I", "Hello", "Initial value"],
                    ]

class Maker(object):
    implements(service.IServiceMaker, IPlugin)
    tapname = 'mailbox'
    description = "CA Server with a Mailbox PV"
    options = Options

    def makeService(self, options):
        
        server = staticserver.StaticPVServer()
        
        dbf = string2DBF(options['dbf'])
        maxcount = int(options['maxcount'])

        pv = mailbox.MailboxPV(dbf, maxcount, udf=False)
        
        iv = options['initial'][:40]
        pad = (40 - len(iv)%40)%40
        iv += '\0'*pad
        
        pv.put(DBR.STRING, 1, iv, None)

        name = options['pv']
        rec,sep,fld = name.partition('.')
        if sep=='':
            name+='.'
        if fld=='':
            name+='VAL'
        server.add(name, pv)
        
        port = int(options['port'])

        return makeCASService(server, port, interface=options['ip'])

serviceMaker = Maker()
