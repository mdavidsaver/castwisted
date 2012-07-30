# -*- coding: utf-8 -*-
"""
Created on Sun Jul 29 16:04:17 2012

@author: mdavidsaver
"""

import weakref
import logging
L = logging.getLogger('TwCAS.protocol')

from zope.interface import implements

from twisted.internet.protocol import connectionDone
from twisted.protocols.stateful import StatefulProtocol
from twisted.internet.defer import Deferred

from interface import INameServer, IPVServer, IPVRequest

import ECA
import caproto
from caproto import caheader, caheaderext, caheaderlarge

class PVConnect(object):
    """A request by the Peer to create a channel connecting to a PV
    """
    implements(IPVRequest)
    def __init__(self, proto, sid, cid, pvname, client):
        self.__proto = weakref.ref(proto)
        self.cid = cid
        self.sid = sid
        self.pv = pvname
        self.client = client
        self.clientVersion = proto.peerVersion
        self.__replied = False

    @property
    def replied(self):
        return self.__replied

    def getCircuit(self):
        """Get the circuit from which this request was received.
        
        May return None if the circuit has be lost
        """
        return self.__proto()

    def __check(self):
        assert not self.__replied, 'Attempt to claim channel after previous (dis)claim'
        proto = self.__proto()
        if proto is None or not proto.connected:
            return
        return proto

    def claim(self, PV):
        proto = self.__check()
        if proto is None:
            return
        
        chan = proto.pvserv.buildChannel(self, PV)
        
        dbr, maxcount, rights = PV.getInfo(self)
        
        proto.addChannel(chan)
        
        try:
            
            msg  = caheader.pack(22, 0, 0, 0, self.cid, rights)
            msg += caheader.pack(18, 0, dbr, maxcount, self.cid, self.sid)
            proto.transport.write(msg)
            self.__replied = True

        except:
            proto.dropSID(chan.sid)
            raise

        return chan

    def disclaim(self):
        proto = self.__check()
        if proto is None:
            return
        
        proto.dropSID(self.sid)
        self.__replied = True

        msg = caheader.pack(26, 0, 0, 0, self.cid, 0)
        proto.transport.write(msg)

class CASTCP(StatefulProtocol):
    
    def __init__(self, pvserver, prio=0, nameserv=None):
        self.pvserv = pvserver
        assert IPVServer.providedBy(pvserver)

        self.nameserv = nameserv
        if self.nameserv is not None:
            assert INameServer.providedBy(nameserv)
        elif INameServer.providedBy(pvserver):
            self.nameserv = pvserver

        # Run when the circuit is being closed
        self.onShutdown = Deferred()
        
        self.prio = prio
        
        self.__header = None
        
        self.peerVersion = 0
        self.peerUser = '<Unknown>'
        
        self.__nextchanid = 0
        self.__channels = {}

    @property
    def connected(self):
        return self.__channels is not None

    def nextSID(self):
        I = self.__nextchanid
        while I in self.__channels:
            I += 1
        self.__nextchanid = I+1
        return I

    def dropSID(self, sid):
        del self.__channels[sid]

    def addChannel(self, chan):
        assert self.__channels.pop(chan.sid, None) is None, "Attempt to reuse channel %d"%chan.sid
        self.__channels[chan.sid] = chan

    def dropChannel(self, chan):
        if self.__channels.pop(chan.sid, None) is chan:
            msg = caheader.pack(27, 0, 0, 0, chan.cid, 0)
            self.transport.write(msg)

    def connectionMade(self):
        # before Base 3.14.12 servers didn't send version until client authenticated
        # from 3.14.12 clients attempting to do TCP name resolution don't authenticate
        # but expect a version message immediately
        msg = caheader.pack(0, 0, self.prio, caproto.VERSION, 0, 0)
        self.transport.write(msg)


    def connectionLost(self, reason):
        if reason is connectionDone:
            self.onShutdown.callback(None)
        else:
            self.onShutdown.errback(reason)
        for chan in self.__channels.values(): # iterates on a copy
            chan.channelClosed()
        # at this point the circuit object is defuct...
        self.__channels = None

    def getInitialState(self):
        return (self.header1, caheader.size)

    def header1(self, data):
        cmd, blen, dtype, dcount, p1, p2 = caheader.unpack(data)
        
        if blen==0:
            # short message w/o payload.  Dispatch directly
            self.__dispatch.get(cmd, self.__ignore)(self, cmd, dtype, dcount, p1, p2, payload='')
            return None # Next packet

        self.__header = (cmd, blen, dtype, dcount, p1, p2)

        if blen==0xffff and dcount==0:
            # long message.  Must wait for extended header
            return (self.header2, caheaderext.size)
        else:
            return (self.payload, blen)

    def header2(self, data):
        cmd, blen, dtype, dcount, p1, p2 = self.__header
        
        blen, dcount = caheaderext.unpack(data)
        
        self.__header = (cmd, blen, dtype, dcount, p1, p2)

        return (self.payload, blen)

    def payload(self, data):
        cmd, blen, dtype, dcount, p1, p2 = self.__header
        self.__header = None

        try:
            self.__dispatch.get(cmd, self.__ignore)(self, cmd, dtype, dcount, p1, p2, payload=data)
        except caproto.CAProtoFault,e:
            L.fatal('Connection from %s closed after protocol error', self.transport.getPeer())
            self.transport.loseConnection()
        except:
            L.exception('Error processing message %d from: %s', cmd, self.transport.getPeer())

        return (self.header1, caheader.size)

    def __ignore(self, cmd, *args):
        L.debug('Unexpected message %d from %s', cmd, self.transport.getPeer())

    def __version(self, cmd, dtype, dcount, p1, p2, payload):
        self.prio = max(self.prio, dtype)
        self.peerVersion = dcount
        L.info('%s has version %d and wants priority', self.transport.getPeer(), dcount, dtype)

    def __user(self, cmd, dtype, dcount, p1, p2, payload):
        self.peerUser = str(payload).strip('\0')
        L.info("%s is user '%s'", self.transport.getPeer(), self.peerUser)

    def __host(self, cmd, dtype, dcount, p1, p2, payload):
        # We don't trust the peer to self identify
        pass

    def __create(self, cmd, dtype, dcount, p1, p2, payload):
        pv = str(payload).strip('\0')
        if self.peerVersion != p2:
            L.warn('%s attempted to change version from %d to %d',
                   self.transport.getPeer(), self.peerVersion, p2)

        peer = self.transport.getPeer()

        sid = self.nextSID()

        self.__channels[sid] = None # Placeholder until channel is claimed

        connect = PVConnect(self, sid, cid=p1, pvname=pv,
                            client=(peer.host, peer.port))

        try:
            self.pvserv.connectPV(connect)
        except:
            self.__channels.pop(sid, None)
            raise

    def __clear(self, cmd, dtype, dcount, p1, p2, payload):
        chan = self.__channels.pop(p1, None)
        if chan is None:
            L.warn('%s attempts to close channel %d which does not exist',
                   self.transport.getPeer(), p1)
            return

        try:
            if p2 != chan.cid:
                L.error('%s disconnects %d using cid %d instead of %d',
                       self.transport.getPeer(), p2, chan.cid)

            msg = caheader.pack(12, 0, 0, 0, p1, p2)
            
            self.transport.write(msg)

        finally:
            chan.channelClosed()

    def __dispatchP1(self, cmd, dtype, dcount, p1, p2, payload):
        """Dispatch to appropriate channel
        """
        chan = self.__channels.get(p1, None)
        if chan is None:
            self.__fail(None, cmd, dtype, dcount, p1, p2, payload)
            return

        try:
            chan.messageReceived(cmd, dtype, dcount, p1, p2, payload)
        except:
            self.__fail(chan, cmd, dtype, dcount, p1, p2, payload)
            return

    __dispatch = {
         0: __version,
         1: __dispatchP1,
         2: __dispatchP1,
         4: __dispatchP1, # Write
        12: __clear,
        15: __dispatchP1, # Read w/ notify
        18: __create,
        19: __dispatchP1, # Write w/ notify
        20: __user,
        21: __host
    }
