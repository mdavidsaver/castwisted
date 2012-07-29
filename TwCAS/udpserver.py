# -*- coding: utf-8 -*-
"""
Created on Sun Jul 29 10:33:03 2012

@author: mdavidsaver
"""

from caproto import VERSION, caheader, casearchreply, addr2int
from interface import INameServer

from twisted.internet.protocol import DatagramProtocol

class PVSearch(object):
    """Active Search request from a client.
    """
    def __init__(self, cid, pv, endpoint, version, transport,
                 localport, nack=False):
        self.cid=cid
        self.pv=pv
        self.client=endpoint
        self.clientVersion=version
        self.__transport=transport
        self.__defaultport=localport
        self.__replied=False
        self.__nack=nack

    def claim(self, server=(None,None)):
        assert not self.__replied, 'Attempt to send second search reply'

        servip, servport = server
        servport = servport or self.__defaultport
        if servip:
            servip = addr2int(servip)
        else:
            servip = 0xffffffff

        msg = casearchreply.pack(6, 8, servport, 0, servip, self.cid, VERSION)
        self.__transport.write(msg, self.client)
        self.__replied=True

    def disclaim(self):
        assert not self.__replied, 'Attempt to send second search reply'

        if not self.__nack:
            return

        msg = caheader.pack(14, 0, 10, self.clientVersion, self.cid, self.cid)
        self.__transport.write(msg, self.client)
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

        self.__actions.get(cmd, self.__ignore)(self, endpoint, dtype, dcnt, p1, p2, body)
        return remainder

    def __version(self, *args, **kws):
        pass

    def __lookup(self, endpoint, reply, ver, cid, cid2, body):
        pv = str(body).strip('\0')
        search = PVSearch(cid, pv, endpoint, ver, self.transport, self.localport)
        self.nameserv.lookupPV(search)

    def __ignore(self, *args, **kws):
        pass

    __actions={0:__version, 6:__lookup}
