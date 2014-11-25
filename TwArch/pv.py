# -*- coding: utf-8 -*-

import weakref

import logging
_log = logging.getLogger(__name__)

import numpy as np

from zope.interface import implements

from twisted.internet import defer

from TwCAS.protocol.interface import IPVDBR
from TwCAS.dbr import DBF, DBR, valueMake, metaEncode
from TwCAS.protocol import ECA

from carchive.date import makeTimeInterval

class Meta(object):
    def __init__(self, meta):
        self.severity = meta['sevr']
        self.status = meta['stat']
        self.timestamp = (meta['sec'], meta['ns'])

class ArchPV(object):
    implements(IPVDBR)

    def __init__(self, server, breakDown, rec, extra):
        self.name, self.breakDown, self.server = rec, breakDown, server

        self.T0, self.T1 = makeTimeInterval(extra.get('T0',[None])[0],
                                            extra.get('T1',[None])[0])

        _log.info('Open channel for %s  %s -> %s', rec, self.T0, self.T1)

    def getInfo(self, request):
        return (DBF.DOUBLE, 1, 1)

    def put(dtype, dcount, dbrdata, reply=None, chan=None):
        if reply is not None:
            reply.error(ECA.ECA_NOWTACCESS)

    def get(self, request):
        reply.error(ECA.ECA_GETFAIL)
   
    def monitor(self, request):
        if request.dbr!=DBR.TIME_DOUBLE:
            request.error(ECA.ECA_BADTYPE)
            return

        D = self._answer(request)
        request.__D = D # attach to the request to keep our answer alive

    @defer.inlineCallbacks
    def _answer(self, request):
        data = [None, None]
        def store(V,M):
            if data[0] is None:
                data[0] = V
                data[1] = M
            else:
                data[0] = np.concatenate((data[0], V), axis=0)
                data[1] = np.concatenate((data[1], M))

        try:
            _log.info('Begin query %s', self.name)
            N = yield self.server.fetchplot(self.name, store,
                                           T0=self.T0, Tend=self.T1,
                                           count=100, archs=self.server.archs)

            values, metas = data
            for i in range(len(metas)):
                encmeta = encodeMeta(DBR.TIME_DOUBLE, Meta(metas[i]))
                encval = valueMake(DBF.DOUBLE, values[i,:])
                while not request.updateDBR(encmeta+encval, values.shape[1]):
                    yield request.whenReady()
                    # TODO: bounce through main loop

            _log.info('End query %s', self.name)

        except:
            _log.exception('Request fails')
            request.error(ECA.ECA_GETFAIL)
        finally:
            request.__D = None
