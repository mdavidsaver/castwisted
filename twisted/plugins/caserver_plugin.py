# -*- coding: utf-8 -*-

import logging

import ConfigParser
from ConfigParser import SafeConfigParser as Parser

from zope.interface import implements

from twisted.python import usage, log
from twisted.plugin import IPlugin
from twisted.application import service

from TwCAS.application import CAServerService, getPVFactory
from TwCAS.util import staticserver

class Options(usage.Options):
    optFlags = [["verbose", "v", "Verbose Logging"]
                    ]
    optParameters = [["ip", "", "", "Address of interface"],
                     ["port", "", 5064, "CA Server port", int],
                     ["beacon","", 5065, "Beacon port", int],
                     ["config", "c", None, "Configuration file"],
                    ]

    def __init__(self):
        usage.Options.__init__(self)
        self['macro'] = {}
        self.docs['macro']="Macro definition"

    def opt_macro(self, symbol):
        var, _, val = symbol.partition('=')
        if len(val)==0:
            raise usage.UsageError("Malformed macro definition '%s'"%symbol)
        self['macro'][var]=val

    opt_m = opt_macro

    def postOptions(self):
        if not self["config"]:
            raise usage.UsageError("must specify config file")

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
            raise RuntimeError("Failed to open '%s'.  Aborting!"%options['config'])

        parser = Parser(options['macro'])
        
        parser.readfp(fp)
        fp.close()
        
        server = staticserver.StaticPVServer()
        
        for S in parser.sections():
            if parser.has_option(S, 'name'):
                name = parser.get(S, 'name')
            else:
                name= S
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
                pv = factory.build(S, parser)
            except KeyError:
                log.err("Failed to initialize '%s'"%name)
                continue
            
            server.add(name, pv)

        port = options['port']

        return CAServerService(server, tcpport=port, udpport=port,
                               beaconport=options['beacon'],
                               interface=options['ip'])

serviceMaker = Maker()
