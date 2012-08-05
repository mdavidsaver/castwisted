# -*- coding: utf-8 -*-

import weakref
import logging
L = logging.getLogger('TwCAS.protocol')

from zope.interface import implements
from interface import IChannel

from twisted.internet import reactor

import ECA

import caproto

class PutNotify(object):
    def __init__(self, chan, subid, dbr, dcount):
        self.__chan = weakref.ref(chan)
        self.dbr, self.dcount = dbr, dcount
        self.subid = subid

    def __del__(self):
        self.error(ECA.ECA_PUTFAIL)

    @property
    def channel(self):
        return self.__chan()

    def finish(self):
        return self.error(ECA.ECA_NORMAL)

    def error(self, eca):
        chan = self.__chan()
        if chan is None:
            return False

        msg = caproto.caheader.pack(19, 0, self.dbr, self.dcount, eca, self.subid)
        
        #Note: PutNoify replies are never dropped.
        chan.getCircuit().write(msg)
        self.__chan = lambda:None
        return True


class SendData(object):
    def __init__(self, chan, subid, dbr, dcount, mask=-1):
        self.__chan = weakref.ref(chan)
        self.dbr, self.dcount = dbr, dcount
        self.subid, self.mask = subid, mask
        self.complete = False

    def __del__(self):
        if self.complete or not self.once:
            return
        # Attempt to ensure that get response is sent even if this
        # request is discarded without action.

    @property
    def channel(self):
        return self.__chan()

    def _close(self):
        self.__chan = lambda:None
        self.complete = True

    def error(self, eca):
        pass

    def update(self, data, dcount, eca=ECA.ECA_NORMAL):
        """Send DBR data to client
        """
        chan = self.channel
        if self.complete or chan is None or chan.getCircuit().paused:
            return False
        
        if self.dcount or chan.peerVersion<13:
            # Fixed size array
            C = cmp(dcount, self.dcount)
            if C==-1: # dcount < self.dcount
                pass # pad
            elif C==1: # dcount > self.dcount
                pass # truncate
        else:
            # Dynamic array
            if dcount > chan.dcount:
                pass # truncate

        if len(data)>=0xffff or dcount>=0xffff:
            #Large payload
            msg = caproto.caheaderlarge.pack(self.catype, 0xffff, self.dbr,
                                             0, eca, self.subid,
                                             len(data), dcount)
        else:
            msg = caproto.caheader.pack(self.catype, len(data), self.dbr, dcount,
                                        eca, self.subid)

        T = chan.getCircuit()
        T.write(msg)
        T.write(data)
        
        if self.once:
            self._close()

        return True

class Subscription(SendData):
    catype = 1
    once = False

class GetNotify(SendData):
    catype = 15
    once = True


class Channel(object):
    implements(IChannel)

    def __init__(self, request, PV, qsize=4):
        self.__proto = request.getCircuit() # take strong reference (ref loop created)
        assert self.__proto is not None
        self.pv = request.pv
        self.cid = request.cid
        self.sid = request.sid
        self.client = request.client
        self.clientVersion = request.clientVersion
        
        self.dbr, self.maxCount, self.rights = PV.getInfo(request)
        
        self.write = self.__proto.transport.write
        
        self.__Q = []
        self.__Qmax = qsize
        
        self.__subscriptions = {}

    def channelClosed(self):
        """Close due to circuit loss
        """
        self.__proto = None # release strong reference (ref loop broken)

    def close(self):
        """Close and notify client
        """
        self.__proto.dropChannel(self)
        msg = caproto.caheader.pack(27, 0, 0, 0, self.cid, 0)
        self.__proto.transport.write(msg)
        
        for S in self.__subscriptions.itervalues():
            S._close()

        self.channelClosed()

    def messageReceived(self, cmd, dtype, dcount, p1, p2, payload):
        if cmd == 2:
            # Never drop event cancel since this will likely help to 
            # reduced load.
            self.__eventcancel(cmd, dtype, dcount, p1, p2, payload)
        else:
            # decouple request rate through queue
            first = len(self.__Q)==0
            
            if len(self.__Q) >= self.__Q:
                return # drop

            self.__Q.append((cmd, dtype, dcount, p1, p2, payload))

            if first:
                reactor.callLater(0, self.__Qop, None)

    def __Qop(self, ignore):
        args = self.__Q.pop(0)
        self.__actions.get(args[0], self.__ignore)(self, *args)
        if len(self.__Q):
            reactor.callLater(0, self.__Qop, None)


    def getCircuit(self):
        return self.__proto.pmux

    def getPeer(self):
        return self.__proto.transport.getPeer()

    def __eventadd(self, cmd, dtype, dcount, p1, p2, payload):
        if p2 in self.__subscriptions:
            L.error('%s trying to reuse an active subscription ID'%self.getCircuit().transport.getPeer())
            return
        if len(payload) < caproto.casubscript.size:
            L.error('%s tried to create subscription without proper payload'%self.getCircuit().transport.getPeer())
            return
        mask, = caproto.casubscript.unpack(payload)
            
        sub = Subscription(self, p2, dtype, dcount, mask)
        
        self.__subscriptions[sub.subid] = sub
        
        self.pv.monitor(sub)

    def __eventcancel(self, cmd, dtype, dcount, p1, p2, payload):
        sub = self.__subscriptions.pop(p2, None)
        if sub is None:
            L.error('%s trying to cancel unused subscription ID'%self.getCircuit().transport.getPeer())
            return

        msg = caproto.caheader.pack(1, 0, sub.dbr, sub.dcount, self.sid, sub.subid)
        
        self.getCircuit().write(msg)
        
        sub._close()

    def __getnotify(self, cmd, dtype, dcount, p1, p2, payload):

        get = GetNotify(self, p2, dtype, dcount)

        self.pv.get(get)

    def __putnotify(self, cmd, dtype, dcount, p1, p2, payload):
        # TODO: Check consistency of len(payload) and dtype+dcount
        put = PutNotify(self, p2, dtype, dcount)
        
        self.pv.put(dtype, dcount, payload, put)

    def __put(self, cmd, dtype, dcount, p1, p2, payload):
        # TODO: Check consistency of len(payload) and dtype+dcount
        self.pv.put(dtype, dcount, payload, None)

    def __ignore(self, cmd, dtype, dcount, p1, p2, payload):
        pass

    __actions = {
         1: __eventadd, # event add
         2: __eventcancel, # event del
         4: __put, # Write
        15: __getnotify, # Read w/ notify
        19: __putnotify, # Write w/ notify
    }

    def __unicode__(self):
        if self.__proto is None:
            return u'Channel %s for <disconnected>'%(self.pv)
        else:
            P = self.getPeer()
            return u'Channel %s for %s:%d' % (self.pv, P.host, P.port)
