# -*- coding: utf-8 -*-
"""
Created on Sun Jul 29 10:33:03 2012

@author: mdavidsaver
"""

import weakref
import logging
L = logging.getLogger('TwCAS.protocol')

from zope.interface import implements

from caproto import VERSION, caheader, casearchreply, addr2int
from interface import INameServer, IPVRequest

from twisted.internet.protocol import DatagramProtocol

class PVSearch(object):
    """Active Search request from a client.
    """
    implements(IPVRequest)
    sid=None # not applicable to search request/reply
    def __init__(self, cid, pv, endpoint, version, transport,
                 localport, nack=False):
        self.cid=cid
        self.pv=pv
        self.client=endpoint
        self.clientVersion=version
        self.__transport=weakref.ref(transport)
        self.__defaultport=localport
        self.__replied=False
        self.__nack=nack

    def __del__(self):
        # Ensure NACK is sent if the request is forgotten
        if not self.__replied:
            self.disclaim()

    @property
    def replied(self):
        return self.__replied

    def __check(self):
        assert not self.__replied, 'Attempt to send second search reply'
        return self.__transport()

    def claim(self, server=(None,None)):
        transport = self.__check()
        if transport is None or transport.bufferFull:
            return False

        servip, servport = server
        servport = servport or self.__defaultport
        if servip:
            servip = addr2int(servip)
        else:
            servip = 0xffffffff

        msg = casearchreply.pack(6, 8, servport, 0, servip, self.cid, VERSION)
        transport.write(msg, self.client)
        self.__replied=True
        return True

    def disclaim(self):
        transport = self.__check()
        if transport is None or transport.bufferFull:
            return

        if not self.__nack:
            return

        msg = caheader.pack(14, 0, 10, self.clientVersion, self.cid, self.cid)
        transport.write(msg, self.client)
        self.__replied=True

    def __unicode__(self):
        return u'PVSearch(%u,%s)'%(self.cid, self.pv)

class CASUDP(DatagramProtocol):
    """UDP part of CA server protocol.
    
    Supports PV name lookup
    """

    def __init__(self, nameserv, localport):
        assert INameServer.providedBy(nameserv)
        self.nameserv = nameserv
        self.localport = localport

    def startProtocol(self):
        self.transport.bufferFull = False
        self.transport.registerProducer(self, True)

    def datagramReceived(self, message, endpoint):
        message=buffer(message)
        while len(message)>0:
            message = self.__process(message, endpoint)

    def __process(self, message, endpoint):
        cmd, blen, dtype, dcnt, p1, p2 = caheader.unpack_from(message)
        if len(message) < caheader.size + blen:
            # Too short to be a valid CA message so stop processing
            return ''
        body = buffer(message, caheader.size, blen)
        remainder = buffer(message, caheader.size + blen)

        self.__actions.get(cmd, self.__ignore)(self, endpoint, cmd, dtype, dcnt, p1, p2, body)
        return remainder

    def __version(self, *args, **kws):
        pass

    def __lookup(self, endpoint, cmd, reply, ver, cid, cid2, body):
        pv = str(body).strip('\0')
        search = PVSearch(cid, pv, endpoint, ver, self.transport, self.localport)
        self.nameserv.lookupPV(search)

    def __ignore(self, junk, endpoint, cmd, *args, **kws):
        L.debug('Unexpected UDP message %d from %s', cmd, endpoint)

    __actions={0:__version, 6:__lookup}
    
    def resumeProducing(self):
        self.transport.bufferFull = False
    def pauseProducing(self):
        self.transport.bufferFull = True
    def stopProducing(self):
        self.transport.bufferFull = True
