# -*- coding: utf-8 -*-
"""
Created on Sun Jul 29 23:01:30 2012

@author: mdavidsaver
"""

import weakref
import logging
L = logging.getLogger('TwCAS.protocol')

from zope.interface import implements
from interfaces import IChannel

from twisted.internet import reactor
from twisted.internet.defer import DeferredQueue

import ECA

import caproto

class SendData(object):
    def __init__(self, chan, subid, dbr, dcount, mask=-1):
        self.__chan = weakref.ref(chan)
        self.dbr, self.dcount = dbr, dcount
        self.subid, self.mask = subid, mask
        self.complete = False

    def __del__(self):
        if self.complete or not self.once:
            return
        # Ensure that get response is sent even if this request is discarded
        # without action

    @property
    def channel(self):
        return self.__chan()

    def _close(self):
        self.__chan = lambda:None
        self.complete = True

    def update(self, data, dcount):
        if complete:
            return
        chan = self.channel
        
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
                                             0, ECA.ECA_NORMAL, self.subid,
                                             len(data), dcount)
        else:
            msg = caproto.caheader.pack(self.catype, len(data), self.dbr, dcount,
                                        ECA.ECA_NORMAL, self.subid)

        T = chan.getCircuit().transport
        T.write(msg)
        T.write(data)
        
        if self.once:
            self._close()

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
        self.__proto = None # release strong reference (ref loop broken)

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
        return self.__proto

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
        
        self.getCircuit().transport.write(msg)
        
        sub._close()

    def __getnotify(self, cmd, dtype, dcount, p1, p2, payload):
        
        get = GetNotify(self, p2, dtype, dcount)
        
        self.pv.

    def __putnotify(self, cmd, dtype, dcount, p1, p2, payload):
        pass

    def __put(self, cmd, dtype, dcount, p1, p2, payload):
        pass

    def __ignore(self, cmd, dtype, dcount, p1, p2, payload):
        pass

    __actions = {
         1: __eventadd, # event add
         2: __eventcancel, # event del
         4: __put, # Write
        15: __getnotify, # Read w/ notify
        19: __putnotify, # Write w/ notify
    }
