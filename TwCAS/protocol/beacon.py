# -*- coding: utf-8 -*-

from twisted.internet.task import LoopingCall
from twisted.internet.protocol import DatagramProtocol

import socket
from caproto import VERSION, caheader, addr2int

from TwCAS import getLogger, PrefixLogger
L = getLogger(__name__)

from TwCAS.util.ifinspect import getifinfo

class BeaconProtocol(DatagramProtocol):
    """Announces the availability of a CA TCP server
    on specified connected interfaces.
    """
    def __init__(self, period, tcpport, udpport=5065, ifaces=[], auto=True):
        self.L = PrefixLogger(L, self)

        self.period = period
        self.T = LoopingCall(self.pushBeacon)
        
        self.port, self.portnum = udpport, tcpport

        self.ifaces, self.autoiface = set(ifaces), auto
        
        self.cnt = 0

    def startProtocol(self):

        self.ips = []
        for IF in getifinfo():
            if IF.broadcast and (self.autoiface or IF.broadcast in self.ifaces):
                self.ips.append((IF.broadcast,IF.addr))

        
        self.L.info('Server %u through %u',self.portnum,self.port)
        if len(self.ips):
            self.L.info('using %s',self.ips)
        else:
            self.L.warn('Not announcing on any interfaces!')

        self.ips = [(bc,addr2int(ip)) for (bc,ip) in self.ips]
        
        self.T.start(self.period)

    def stopProtocol(self):
        self.T.stop()

    def pushBeacon(self):
        for ip, num in self.ips:
            msg = caheader.pack(13, 0, VERSION, self.portnum, self.cnt, num)

            try:
                self.transport.write(msg, (ip,self.port))
            except socket.error,e:
                self.L.error('Send to %s:%u error %s', ip, self.port, e)

        self.cnt += 1

    def datagramReceived(self, data, src):
        pass # ignore

    def __str__(self):
        return 'BeaconProtcol(%u,%u)'%(self.period, self.port)
    def __repr__(self):
        return self.__str__()
