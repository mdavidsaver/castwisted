# -*- coding: utf-8 -*-

import logging

import ConfigParser
from ConfigParser import SafeConfigParser as Parser

from zope.interface import implements

from twisted.python import usage, log
from twisted.plugin import IPlugin
from twisted.application import service

from TwCAS.application import CAServerService

from TwArch.server import ArchiveServer

class Options(usage.Options):
    optFlags = [["verbose", "v", "Verbose Logging"]
                    ]
    optParameters = [["ip", "", "", "Address of interface"],
                     ["port", "", 5064, "CA Server port", int],
                     ["beacon","", 5065, "Beacon port", int],
                    ]


class Maker(object):
    implements(service.IServiceMaker, IPlugin)
    tapname = 'archserver'
    description = "Static CA Server"
    options = Options

    def makeService(self, options):

        lvl = logging.DEBUG if options['verbose'] else logging.ERROR

        logging.basicConfig(level=lvl)

        server = ArchiveServer('DEFAULT')
        port = options['port']

        return CAServerService(server, tcpport=port, udpport=port,
                               beaconport=options['beacon'],
                               interface=options['ip'])

serviceMaker = Maker()
