# -*- coding: utf-8 -*-

import logging
L = logging.getLogger('TwCAS.mailboxpv')

import weakref

from zope.interface import implements

from TwCAS.interface import IPVDBR

from TwCAS import DBR, ECA, caproto

__all__ = ['MailboxPV']

class MailboxPV(object):
    """A PV which stores DBR data sent to it.
    
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
        for mon in self.__monitors.values():
            self.get(mon)

        if reply:
            reply.finish()

    def monitor(self, request):

        L.debug('%s monitor dbr:%d', self, request.dbr)
        self.get(request)
        self.__monitors[id(request)]=request
