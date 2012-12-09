# -*- coding: utf-8 -*-

import logging
L = logging.getLogger('TwCAS.pvs')

import weakref, struct

from zope.interface import implements

from twisted.internet import reactor

from TwCAS.interface import IPVDBR

from TwCAS import ECA, caproto
from TwCAS import dbr as DBR

__all__ = ['DynamicMailboxPV'
          ,'ClientInfo'
          ,'Spam'
          ]

class DynamicMailboxPV(object):
    """A PV which stores any DBR data sent to it.
    
    It does not support type conversions.
    
    New channels see the current stored DBR type reported as native.
    
    Meta information is always zero
    """
    implements(IPVDBR)
    
    def __init__(self, firstdbf=0, maxCount=1):
        self.maxCount = maxCount
        self.dbf = firstdbf
        self.count = 1
        self.value = '\0'*DBR.dbf_element_size(firstdbf)
        #self.__meta = ''
        
        self.__monitors = weakref.WeakValueDictionary()

    def getInfo(self, request):
        return (self.dbf, self.maxCount, 3)

    def get(self, request):
        dbf, mlen = DBR.dbr_info(request.dbr)

        L.debug('%s get dbr:%d', self, request.dbr)
        
        if dbf != self.dbf:
            request.error(ECA.ECA_NOCONVERT)
            return
        meta = '\0'*mlen

        data = self.value
        dcount = self.count

        # it may be slightly more efficent to add the padding
        # when concatinating meta to data
        pad = caproto.pad(len(meta)+len(data))

        request.update('%s%s%s'%(meta,data,pad), dcount)

    def put(self, dtype, dcount, dbrdata, reply):
        dbf, mlen = DBR.dbr_info(dtype)

        L.debug('%s put dbr:%d', self, dtype)

        self.dbf = dbf
        #self.__meta = dbrdata[:mlen]
        self.value = dbrdata[mlen:]
        self.count = dcount

        # update monitors
        Ms=self.__monitors.values()
        L.debug('%s post to %d subscribers', self, len(Ms))
        for mon in Ms:
            self.get(mon)

        if reply:
            reply.finish()

    def monitor(self, request):

        L.debug('%s monitor dbr:%d', self, request.dbr)
        self.get(request)
        self.__monitors[id(request)]=request

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
        request.update(msg, 1)

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
        request.update(msg, 1)

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
            if not request.update(msg, 1):
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
