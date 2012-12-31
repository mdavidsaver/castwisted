# -*- coding: utf-8 -*-

import logging
L = logging.getLogger('TwCAS.service.sum')

from TwCAS import dbr
from TwCAS.util import service

class SumSession(service.SessionBase):
    
    def __init__(self, *args, **kws):
        service.SessionBase.__init__(self, *args, **kws)
        # Initialize this session's state
        self.sum = 0.0
        # This service doesn't do anything w/ meta-data
        # so keep some null meta-data to give to clients.
        self._meta = dbr.DBRMeta()
    
    def getInfo(self):
        L.info("Opening Sum Session with %s"%self.channel)
        # Always appear as a R/W scalar double
        return (dbr.DBF.DOUBLE, 1, 3)

    def disconnect(self):
        L.info("Closed Sum session with %s"%self.channel)

    def put(self, dtype, dcount, dbrdata, reply=None, chan=None):
        # Try to convert whatever the user sends to
        # a double array (CA data is always an array)
        val, meta = dbr.DBR2Py(dtype, dcount, dbrdata,
                               dbf=dbr.DBF.DOUBLE)

        L.debug('Sum session %f += %f  (%s)'%(self.sum, val[0], self.channel))

        self.sum += val[0]

        # Notify subscribers.  By default SessionBase turns in
        # into calls to self.get()
        self.post()
        # If the client requested completion notification,
        # then give it.
        if reply:
            reply.finish()

    def get(self, request):
        # Provide the current sum.
        request.update([self.sum], self._meta, dbf=dbr.DBF.DOUBLE)

# register this service
sumfactory = service.ServiceFactory('Sum', SumSession)
