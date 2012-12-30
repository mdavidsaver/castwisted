# -*- coding: utf-8 -*-

import logging
L = logging.getLogger('TwCAS.service.sum')

from TwCAS import dbr
from TwCAS.util import service

class SumSession(service.SessionBase):
    
    def __init__(self, *args, **kws):
        service.SessionBase.__init__(self, *args, **kws)
        self.sum = 0.0
        self._meta = dbr.DBRMeta()
    
    def getInfo(self):
        L.info("Opening Sum Session with %s"%self.channel)
        return (dbr.DBF.DOUBLE, 1, 3)

    def disconnect(self):
        L.info("Closed Sum session with %s"%self.channel)

    def put(self, dtype, dcount, dbrdata, reply=None, chan=None):
        val, meta = dbr.DBR2Py(dtype, dcount, dbrdata,
                               dbf=dbr.DBF.DOUBLE)

        L.debug('Sum session %f += %f  (%s)'%(self.sum, val[0], self.channel))

        self.sum += val[0]

        self.post()
        if reply:
            reply.finish()

    def get(self, request):
        request.update([self.sum], self._meta, dbf=dbr.DBF.DOUBLE)

sumfactory = service.ServiceFactory('Sum', SumSession)
