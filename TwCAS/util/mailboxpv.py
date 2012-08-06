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
    
    def __init__(self, firstdbf=0):
        self.dbf = firstdbf
        self.count = 1
        self.value = '\0'*DBR.dbf_element_size(firstdbf)
        #self.__meta = ''
        
        self.__monitors = weakref.WeakValueDictionary()

    def getInfo(self, request):
        return (self.dbf, self.count, 3)

    def get(self, request):
        dbf, mlen = DBR.dbr_info(request.dbr)
        if dbf != self.dbf:
            request.error(ECA.ECA_NOCONVERT)
            return
        meta = '\0'*mlen

        if request.dynamic:
            # dynamic array.  so return what we have
            data = self.value
            dcount = self.count
        else:
            # always give the requested size
            dlen = DBR.dbr_size(dbf, request.dcount)
            if dlen > len(self.value):
                # zero pad
                data = self.value + '\0'*(dlen-len(self.value))
            elif dlen < len(self.value):
                # truncate
                data = self.value[:dlen]
            else:
                data = self.value
            dcount = request.dcount

        # it is slightly more efficent to add the padding
        # when concatinating meta to data
        pad = caproto.pad(len(meta)+len(data))

        request.update('%s%s%s'%(meta,data,pad), dcount)

    def put(self, dtype, dcount, dbrdata, reply):
        dbf, mlen = DBR.dbr_info(dtype)

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
        self.get(request)
        self.__monitors[id(request)]=request
