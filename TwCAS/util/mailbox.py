# -*- coding: utf-8 -*-

import logging
L = logging.getLogger('TwCAS.mailbox')

import weakref, time

from TwCAS.dbr.xcodeValue import np

from zope.interface import implements

from twisted.internet import reactor

from TwCAS.interface import IPVDBR

from TwCAS import ECA
from TwCAS import dbr as DBR
from TwCAS.dbr.defs import POSIX_TIME_AT_EPICS_EPOCH

class MailboxPV(object):
    """A PV which stores DBR data of a specific type.
    
    Data of other types will be converted if possible.

    Sends monitor updates on value or meta-data change.

    Handles update of meta-data by client.
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
        elif request.dbr==DBR.DBR.CLASS_NAME:
            request.update(self.__class__.__name__[:40], 1)
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
            L.exception("Failed to convert value from DBF %d to DBR %d",
                        self.dbf, request.dbr)

    def monitor(self, request):
        self.get(request)
        if request.complete:
            return
        self.__subscriptions[request] = None

    def put(self, dtype, dcount, dbrdata, reply=None, chan=None):
        if dtype in [DBR.DBR.STSACK_STRING, DBR.DBR.CLASS_NAME]:
            if reply:
                reply.error(ECA.ECA_BADTYPE)
            return
        #L.debug("Put %d %d", dtype,dcount)
        # Alarm ACKs don't get queued.
        if dtype in [DBR.DBR.PUT_ACKT, DBR.DBR.PUT_ACKS]:
            if dcount!=1:
                reply.error(ECA.ECA_PUTFAIL)
                
            val = DBR.valueDecode(DBR.DBR.SHORT, dbrdata, dcount)[0]

            if dtype==DBR.DBR.PUT_ACKT:
                self.__meta.ackt  = 1 if val else 0
            elif val >= getattr(self.__meta, 'acks', 0):
                # dtype==DBR.DBR.PUT_ACKS
                self.__meta.acks = 0

            for M in self.__subscriptions.keys():
                if M.dbr==DBR.DBR.STSACK_STRING:
                    self.get(M)
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
            if not self.__meta.ackt and self.__meta.severity >= self.__meta.acks:
                self.__meta.acks = self.__meta.severity
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
