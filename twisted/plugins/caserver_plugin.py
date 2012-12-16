# -*- coding: utf-8 -*-

import logging

import ConfigParser
from ConfigParser import SafeConfigParser as Parser

from zope.interface import implements

from twisted.python import usage, log
from twisted.plugin import IPlugin
from twisted.application import service

from TwCAS.application import makeCASService, getPVFactory
from TwCAS.util import staticserver

class Options(usage.Options):
    optFlags = [["verbose", "v", "Verbose Logging"]
                    ]
    optParameters = [["ip", "", "127.0.0.1", "Address of interface"],
                     ["port", "", "5064", "CA Server port"],
                     ["config", "c", "", "Configuration file"],
                    ]

class Maker(object):
    implements(service.IServiceMaker, IPlugin)
    tapname = 'caserver'
    description = "Static CA Server"
    options = Options

    def makeService(self, options):

        lvl = logging.DEBUG if options['verbose'] else logging.ERROR

        logging.basicConfig(level=lvl)

        try:
            fp = open(options['config'], 'r')
        except IOError:
            log.err("Failed to open '%s'.  Aborting!", options['config'])
            return None

        parser = Parser()
        
        parser.readfp(fp)
        fp.close()
        
        server = staticserver.StaticPVServer()
        
        for S in parser.sections():
            name = S
            rec,sep,fld = name.partition('.')
            if sep=='':
                name+='.'
            if fld=='':
                name+='VAL'

            try:
                pvtype = parser.get(S, 'type')
            except ConfigParser.NoOptionError:
                log.err("no PV type for '%s'"%name)
                continue

            try:
                factory = getPVFactory(pvtype)
            except KeyError:
                log.err("Unknown PV type '%s' for '%s'"%(pvtype,name))
                continue
            try:
                pv = factory(S, parser)
            except KeyError:
                log.err("Failed to initialize '%s'"%name)
                continue
            
            server.add(name, pv)

        port = int(options['port'])

        return makeCASService(server, port, interface=options['ip'])

serviceMaker = Maker()
