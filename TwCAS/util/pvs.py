# -*- coding: utf-8 -*-

import logging
L = logging.getLogger('TwCAS.mailboxpv')

import weakref, struct, time, traceback

try:
    import numpy as np
except ImportError:
    np = None

from zope.interface import implements

from twisted.internet import reactor

from TwCAS.interface import IPVDBR

from TwCAS import ECA, caproto
from TwCAS import dbr as DBR
from TwCAS.dbr.defs import POSIX_TIME_AT_EPICS_EPOCH

__all__ = ['DynamicMailboxPV'
          ,'MailboxPV'
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

class MailboxPV(object):
    """A PV which stores DBR data of a specific type.
    
    Data of other types will be converted if possible
    """
    implements(IPVDBR)
    longStringSize = 128
    perms = 3
    
    def __init__(self, dbf, maxcount, initial=None, udf=True):
        self.dbf, self.maxCount = dbf, maxcount
        self.__meta = DBR.DBRMeta()
        if maxcount<1:
            raise ValueError("maxcount must be >= 1")
        if initial is None:
            initial = [0] if dbf is not DBR.DBF.STRING else ['']
        self.value = DBR.valueMake(dbf, initial)
        if not udf:
            self.__meta.severity = 0
            self.__meta.status = 0
        self.__subscriptions = weakref.WeakKeyDictionary()
        self.__lastput = None # Cache for most recent pending put requests

    def getInfo(self, request):
        if self.dbf==DBR.DBF.STRING and self.maxCount==1 and \
                getattr(request, 'options', '')=='$':
            # long string
            return (DBR.DBF.UCHAR, self.longStringSize, self.perms)
        else:
            return (self.dbf, self.maxCount, self.perms)

    def get(self, request):
        if request.dbr in [DBR.DBR.PUT_ACKT, DBR.DBR.PUT_ACKS]:
            request.error(ECA.ECA_BADTYPE)
            return

        try:
            val, M = DBR.convert.castDBR(request.dbf, self.dbf,
                                         self.value, self.__meta)
            dlen = len(val)
            val = DBR.valueEncode(request.dbf, self.value)
            M = DBR.metaEncode(request.dbr, M)
            
            assert len(M)==request.metaLen, "Incorrect meta encoding"
            
            request.update(M+val, dlen)

        except ValueError:
            request.error(ECA.ECA_NOCONVERT)
            traceback.print_exc()

    def monitor(self, request):
        self.get(request)
        if request.complete:
            return
        self.__subscriptions[request] = None

    def put(self, dtype, dcount, dbrdata, reply):
        if dtype in [DBR.DBR.STSACK_STRING, DBR.DBR.CLASS_NAME]:
            if reply:
                reply.error(ECA.ECA_BADTYPE)
            return
        # Alarm ACKs don't get queued.
        if dtype in [DBR.DBR.PUT_ACKT, DBR.DBR.PUT_ACKS]:
            #TODO: Handle these
            if reply:
                reply.error(ECA.ECA_BADTYPE)
            return

        active = self.__lastput is not None
        self.__lastput = (dtype, dcount, dbrdata, reply)
        if not active:
            reactor.callLater(0, self._put)

    def _put(self):
        dtype, dcount, dbrdata, reply = self.__lastput
        self.__lastput = None
        try:
            self._put2(dtype, dcount, dbrdata, reply)
            if reply and not reply.complete:
                reply.finish()
        except:
            if reply:
                reply.error(ECA.ECA_PUTFAIL)
            raise

    def _put2(self, dtype, dcount, dbrdata, reply):
        dbf, metaLen = DBR.dbr_info(dtype)
        
        M = DBR.DBRMeta(udf=None)

        val = DBR.valueDecode(dbf, dbrdata[metaLen:], dcount)
        DBR.metaDecode(dtype, dbrdata[:metaLen], M)

        val, M = DBR.castDBR(self.dbf, dbf, val, M)

        events = 0

        if np:
            if np.any(val!=self.value):
                events |= DBR.DBE.VALUE | DBR.DBE.ARCHIVE
        else:
            if val!=self.value:
                events |= DBR.DBE.VALUE | DBR.DBE.ARCHIVE
        self.value = val

        try:
            if M.severity!=self.__meta.severity or M.status!=self.__meta.status:
                events |= DBR.DBE.ALARM
            self.__meta.severity = M.severity
            self.__meta.status = M.status
        except AttributeError:
            pass # sender did not include alarm info

        try:
            self.__meta.timestamp = M.timestamp
        except AttributeError:
            # sender did not include timestamp
            now = time.time()
            self.__meta.timestamp = (int(now)-POSIX_TIME_AT_EPICS_EPOCH,
                                     int((now%1)*1e9))

        # TODO: update GR and CTRL meta data
        
        for M in self.__subscriptions.keys():
            if M.mask&events:
                self.get(M)

        if reply:
            reply.finish()

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
