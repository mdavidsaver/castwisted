# -*- coding: utf-8 -*-
"""
Created on Sun Jul 29 16:04:17 2012

@author: mdavidsaver
"""

import weakref

from zope.interface import implements

from twisted.internet import reactor
from twisted.internet.error import ConnectionDone
from twisted.internet.protocol import ServerFactory
from twisted.protocols.stateful import StatefulProtocol
from twisted.internet.defer import Deferred
from twisted.internet.interfaces import IPushProducer

from TwCAS import PrefixLogger, getLogger
L = getLogger(__name__)

from interface import INameServer, IPVServer, IPVRequest

import caproto
from caproto import caheader, caheaderext

from udpserver import PVSearch

from PMux import MuxProducer

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
        self.clientUser = proto.peerUser
        self.__replied = False

    def __del__(self):
        # Ensure NACK is sent if the request is forgotten
        if not self.__replied:
            self.disclaim()

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
            return None
        
        chan = proto.pvserv.buildChannel(self, PV)
        
        proto.addChannel(chan)
        
        try:
            #TODO: Does not check for buffer full condition
            msg  = caheader.pack(22, 0, 0, 0, self.cid, chan.rights)
            msg += caheader.pack(18, 0, chan.dbr, chan.maxCount, self.cid, self.sid)
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

    def __unicode__(self):
        return u'PVConnect(%u,%s)'%(self.cid, self.pv)

class CASTCP(StatefulProtocol):
    implements(IPushProducer)
    
    # Circuit inactivity timeout
    timeout = 60.0
    
    def __init__(self, pvserver, prio=0, nameserv=None, localport=-1):
        self.L = PrefixLogger(L, self)

        assert localport>0, "Invalid local server port"
        self.pvserv = pvserver
        assert IPVServer.providedBy(pvserver)

        self.localport = localport
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
        
        self.__nextchanid = 2 # start a 2 so we avoid sid==ECA_NORMAL
        self.__channels = {}
        
        self.pmux = None

    @property
    def connected(self):
        return self.__channels is not None

    def nextSID(self):
        I = self.__nextchanid
        while I in self.__channels:
            I += 1
        if I>=0xffffffff:
            I = 2
        else:
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
        self.transport.bufferSize = 8*1024
        P = self.transport.getPeer()
        self.clientStr = '%s:%d'%(P.host, P.port)
        self.L.debug('Open Connection from %s', self.clientStr)
        # before Base 3.14.12 servers didn't send version until client authenticated
        # from 3.14.12 clients attempting to do TCP name resolution don't authenticate
        # but expect a version message immediately
        self.transport.bufferFull = False # flag used by PVSearch
        self.pmux = MuxProducer(self.transport)
        C = self.pmux.getConsumer()
        C.registerProducer(self, True)
        msg = caheader.pack(0, 0, self.prio, caproto.VERSION, 0, 0)
        self.transport.write(msg)
        
        self.inactivity = reactor.callLater(self.timeout,
                                            self.transport.loseConnection)

    def connectionLost(self, reason):
        self.L.debug('Close Connection')
        if reason.check(ConnectionDone):
            self.onShutdown.callback(None)
        else:
            self.onShutdown.errback(reason)
        for chan in self.__channels.values(): # iterates on a copy
            chan.channelClosed()
        # at this point the circuit object is defuct...
        self.__channels = None
        self.pmux = None
        try:
            I, self.inactivity = self.inactivity, None
            I.cancel()
        except:
            pass

    def resumeProducing(self):
        self.transport.bufferFull = False
    def pauseProducing(self):
        self.transport.bufferFull = True
    def stopProducing(self):
        self.transport.bufferFull = True

    def getInitialState(self):
        """Entry point for message processing state machine.
        """
        return (self.header1, caheader.size)

    def header1(self, data):
        """Begin message processing with short header
        """
        self.inactivity.reset(self.timeout)

        cmd, blen, dtype, dcount, p1, p2 = caheader.unpack(data)

        if blen==0:
            # short message w/o payload.  Dispatch directly
            self.__process(cmd, dtype, dcount, p1, p2, payload='')
            return None # Next packet

        self.__header = (cmd, blen, dtype, dcount, p1, p2)

        if blen==0xffff and dcount==0:
            # long message.  Must wait for extended header
            return (self.header2, caheaderext.size)
        else:
            return (self.payload, blen)

    def header2(self, data):
        """Process extended header for large messages
        """
        cmd, blen, dtype, dcount, p1, p2 = self.__header
        
        blen, dcount = caheaderext.unpack(data)
        
        self.__header = (cmd, blen, dtype, dcount, p1, p2)

        return (self.payload, blen)

    def payload(self, data):
        """Process message payload
        """
        cmd, blen, dtype, dcount, p1, p2 = self.__header
        self.__header = None

        self.__process(cmd, dtype, dcount, p1, p2, payload=data)

        return (self.header1, caheader.size)

    def __process(self, cmd, *args, **kws):
        #self.L.debug("RX message %d",cmd)
        try:
            self.__dispatch.get(cmd, self.__ignore)(self, cmd, *args, **kws)
        except caproto.CAProtoFault,e:
            self.L.fatal('Connection closed after protocol error: %s',e)
            self.transport.loseConnection()
        except:
            self.L.exception('Error processing message %d', cmd)

    def __ignore(self, junk, cmd, *args, **kws):
        self.L.debug('Unexpected TCP message %d', cmd)

    def __echo(self, cmd, dtype, dcount, p1, p2, payload):
        msg = caproto.caheader.pack(23, 0, 0, 0, 0, 0)
        self.transport.write(msg)

    def __version(self, cmd, dtype, dcount, p1, p2, payload):
        self.prio = max(self.prio, dtype)
        self.peerVersion = dcount
        self.L.info('Has version %d and wants priority %d', dcount, dtype)

    def __user(self, cmd, dtype, dcount, p1, p2, payload):
        self.peerUser = str(payload).strip('\0')
        self.L.info("Identifies")

    def __host(self, cmd, dtype, dcount, p1, p2, payload):
        # We don't trust the peer to self identify
        pass

    def __create(self, cmd, dtype, dcount, p1, p2, payload):
        pv = str(payload).strip('\0')
        if self.peerVersion != p2:
            self.L.warn('attempts to change version from %d to %d',
                   self.peerVersion, p2)

        P = self.transport.getPeer()

        sid = self.nextSID()

        self.__channels[sid] = None # Placeholder until channel is claimed

        connect = PVConnect(self, sid, cid=p1, pvname=pv,
                            client=(P.host, P.port))

        try:
            self.pvserv.connectPV(connect)
        except:
            self.__channels.pop(sid, None)
            raise

    def __clear(self, cmd, dtype, dcount, p1, p2, payload):
        chan = self.__channels.pop(p1, None)
        if chan is None:
            self.L.warn('Attempts to close unknown channel %d', p1)
            return

        try:
            if p2 != chan.cid:
                self.L.error('disconnects %d using cid %d instead of %d',
                       p2, chan.cid)

            msg = caheader.pack(12, 0, 0, 0, p1, p2)
            
            self.transport.write(msg)

        finally:
            chan.channelClosed()

    def __dispatchP1(self, cmd, dtype, dcount, p1, p2, payload):
        """Dispatch to appropriate channel using SID stored in P1 field
        """
        chan = self.__channels.get(p1, None)
        if chan is None:
            self.L.error("Client innitiated operation on unknown channel: %s",
                    (cmd, dtype, dcount, p1, p2))
            return

        try:
            chan.messageReceived(cmd, dtype, dcount, p1, p2, payload)
        except caproto.CAProtoFault:
            raise
        except:
            self.L.exception("Exception for message %s sent to channel %s",
                        (cmd, dtype, dcount, p1, p2), chan)
            return

    def __lookup(self, cmd, reply, ver, cid, cid2, payload):
        pv = str(payload).strip('\0')
        search = PVSearch(cid, pv, None, ver, self.transport, self.localport)
        self.nameserv.lookupPV(search)

    __dispatch = {
         0: __version,
         1: __dispatchP1, # event add
         2: __dispatchP1, # event del
         4: __dispatchP1, # Write
         6: __lookup,
        12: __clear,
        15: __dispatchP1, # Read w/ notify
        18: __create,
        19: __dispatchP1, # Write w/ notify
        20: __user,
        21: __host,
        23: __echo
    }

    def __str__(self):
        if self.pmux is not None:
            return u'%s@%s' % (self.peerUser,self.clientStr)
        elif self.__channels is not None:
            return u'OPENING'
        else:
            return u'CLOSED'
    def __repr__(self):
        return self.__str__()

class CASTCPServer(ServerFactory):
    def __init__(self, port, pvserver, prio=0, nameserv=None):
        self.__circuits = weakref.WeakValueDictionary()
        self.localport = port
        self.pvserver = pvserver
        self.nameserv = nameserv
        L.info('CA TCP server factory starting')

    def close(self):
        self.__listener.stopListening()
        for C in self.__circuit.values():
            if C.connected:
                C.transport.loseConnection()

    def buildProtocol(self, addr):
        L.debug('Building connection from %s:%d',addr.host,addr.port)
        proto = CASTCP(self.pvserver, prio=0, nameserv=self.nameserv,
                       localport=self.localport)
        self.__circuits[id(proto)]=proto
        return proto
