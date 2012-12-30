# -*- coding: utf-8 -*-

import logging
L = logging.getLogger('TwCAS.pvs')

import weakref, struct

from zope.interface import implements

from twisted.internet import reactor

from TwCAS.interface import IPVDBR

from TwCAS import ECA
from TwCAS import dbr as DBR

__all__ = ['ClientInfo'
          ,'Spam'
          ]

class ClientInfo(object):
    """A PV which tells the client something about itself
    """
    implements(IPVDBR)

    def getInfo(self, request):
        return (0, 1, 1)

    def get(self, request):
        if request.dbf != DBR.DBF.STRING:
            request.error(ECA.ECA_NOCONVERT)
            return

        chan = request.channel
        host, port = chan.client
        user = chan.clientUser

        msg = '%s%s on %s:%d' %('\0'*request.metaLen, user, host, port)
        msg = msg[:40]
        print 'send',msg
        msg += '\0'*(40-len(msg))
        request.updateDBR(msg, 1)

    def monitor(self, request):
        self.get(request)

class Spam(object):
    """A PV which writes incrementing numbers
    to all clients as fast as it can.
    
    Uses circuit flow control to avoid dropping
    any updates.
    """
    implements(IPVDBR)
    
    I = struct.Struct('!I')    
    
    def __init__(self):
        self.monitors = weakref.WeakValueDictionary()

    def getInfo(self, request):
        return (5, 1, 1)

    def _check(self, request):
        if request.dbf!=5:
            request.error(ECA.ECA_BADTYPE)
            return True
        return False

    def get(self, request):
        if self._check(request):
            return
        msg = request.metaLen*'\0' + self.I.pack(0)
        request.updateDBR(msg, 1)

    def monitor(self, request):
        if self._check(request):
            return
        request.__count = 0
        request.__meta = request.metaLen*'\0'
        self.pump(request)

    def pump(self, request):
        while not request.complete:
            c = request.__count
            
            msg = request.__meta + self.I.pack(c)
            if not request.updateDBR(msg, 1):
                # Buffer was full, message not sent
                D = request.whenReady()
                D.addCallback(self.kick, request)
                D.addErrback(lambda D:None) # swallow
                return
                
            if c == 0xffffffff:
                request.__count = 0
            else:
                request.__count += 1

    def kick(self, junk, request):
        reactor.callLater(0, self.pump, request)

class Mutex(object):
    """A PV which allows global synchronization.
    
    Clients should always use put w/ callback
    
    Write 1 to request PV, write 0 or disconnect to cancel/release.
    
    A client takes ownership of a Mutex when the put callback
    completes successfully.  If the client wants to timeout
    a request, and keep the channel open, then it must
    put 0.
    
    Attempts to get or monitor DBR_INT will return 1 if the 
    mutex is locked and 0 otherwise.  Attempts to read
    DBR_STRING will show the "IP:Port" of the current
    owner, or an empty string.
    """
    implements(IPVDBR)

    def __init__(self):
        self.owner = None
        self.__subscriptions = weakref.WeakKeyDictionary()
        self.contenders = []
    
    def getInfo(self, request):
        return (DBR.DBF.LONG, 1, 3)

    def get(self, request):
        if request.dbf not in [DBR.DBF.LONG, DBR.DBF.STRING]:
            request.error(ECA.ECA_BADTYPE)
            return

        if request.dbf==DBR.DBF.LONG:
            val = 1 if self.owner else 0

        elif request.dbf==DBR.DBF.STRING:
            if self.owner:
                C = self.owner()
                val = '%s@%s:%s'%(C.clientUser, C.client[0], C.client[1])
                val = val[:40]
            else:
                val = ''

        data = DBR.valueMake(request.dbf, [val])
        data = DBR.valueEncode(request.dbf, data)
        
        request.updateDBR(request.metaLen*'\0' + data, 1)

    def monitor(self, request):
        self.get(request)
        if request.complete:
            return
        self.__subscriptions[request] = None

    def notify(self):
        for M in self.__subscriptions.keys():
            if M.mask&(DBR.DBE.VALUE|DBR.DBE.ARCHIVE):
                self.get(M)

    def _dropowner(self, x):
        if self.owner is not x:
            return

        ochan = None
        while len(self.contenders):
            oreply = self.contenders.pop(0)
            ochan = oreply.channel
            if not ochan.active:
                continue
            ochan = weakref.ref(ochan, self._dropowner)
            oreply.finish()
        self.owner = ochan
        if self.owner:
            L.info("%s now owns", self.owner().client)
        else:
            L.info("Now free")
        self.notify()

    def put(self, dtype, dcount, dbrdata, reply=None, chan=None):
        if not reply:
            return # Client must wait for completion

        if dtype in [DBR.DBR.STSACK_STRING, DBR.DBR.CLASS_NAME]:
            if reply:
                reply.error(ECA.ECA_BADTYPE)
            return

        dbf, metaLen = DBR.dbr_info(dtype)

        val = DBR.valueDecode(dbf, dbrdata[metaLen:], dcount)
        
        M = DBR.DBRMeta() # dummy meta for conversion
        
        val, M = DBR.castDBR(DBR.DBF.LONG, dbf, val, M)

        if val and chan is self.owner:
            # Recursive locking not supported
            reply.error(ECA.ECA_PUTFAIL)

        elif val and self.owner:
            # take contended mutex
            self.contenders.append(reply)
            L.info("%s waiting", str(chan.client))
            # Don't complete reply

        elif val and not self.owner:
            # take uncontended mutex
            self.owner = weakref.ref(chan, self._dropowner)
            self.notify()
            L.info("%s takes", str(chan.client))
            reply.finish()

        elif not val and not self.owner:
            L.info("%s release of free mutex?", str(chan.client))
            reply.finish()

        elif not val and chan is self.owner():
            # release owned mutex
            L.info("%s releases", self.owner().client)
            self._dropowner(self.owner)
            reply.finish()

        elif not val:
            # Cancel all pending request for this channel
            self.contenders=filter(lambda r:r.channel is chan, self.contenders)
            L.info("%s cancels",str(chan.client))
            reply.finish()

        else:
            reply.finish()
            L.error("Logic error!")
