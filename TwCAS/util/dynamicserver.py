# -*- coding: utf-8 -*-

import logging
L = logging.getLogger('TwCAS.dynamicserver')

from zope.interface import implements

from twisted.internet import reactor

from TwCAS.interface import INameServer, IPVServer, IPVDBR

from TwCAS.channel import Channel
from TwCAS.util import splitPVName, InvalidPVNameError

class _CacheEntry(object):
    def __init__(self, name=None, pv=None):
        self.name, self.pv = name, pv

class DynamicPVServer(object):
    """Serves PVs which are created dynamically.
    
    Handles tracking of channels.
    
    Implementations must provide havePV() method, and optionally
    needPV() method.
    """
    implements(INameServer, IPVServer)
    
    cacheCleanPeriod = 15.0
    
    rejectPV = object()
    acceptPV = object()

    def __init__(self, reactor=reactor):
        self.reactor = reactor
        self.__nak_cache = set()
        self.__clean = None

    def clear(self):
        if self.__clean:
            self.__clean.cancel()
            self.__clean = None
        self.__nak_cache = set()

    def havePV(self, rec, fld, options, request):
        """Test to see if this server can provide the requested PV.
        Called when a client is searching for a PV.
        
        Return None to indicate that this server can not provide
            this PV at the moment.
        Returning self.rejectPV is the same as None, but will ignore
            future requests from this client until the next cache flush.
        Return self.acceptPV indicates that this server can provide the
            PV.  IF a client actually connects then self.needPV will be
            called.
        """
        return self.rejectPV

    def needPV(self, rec, fld, options, request):
        """A client is attempting to open a channel to a PV.
        
        Return None to fail the connection, or an object implementing
            the IPVDBR interface.
        """
        return None

    def lookupPV(self, search):
        K = (search.client, search.pv)
        # Bail quickly if previously rejected
        if K in self.__nak_cache:
            self.__addCache(K)
            search.disclaim()
            return

        try:
            rec, fld, extra = splitPVName(search.pv)
        except InvalidPVNameError:
            search.disclaim()
            return
        L.debug('Lookup %s'%search.pv)

        try:
            O = self.havePV(rec, fld, extra, search)
            if O is self.acceptPV or IPVDBR.implements(O):
                search.claim()
            elif O is self.rejectPV or O is None:
                search.disclaim()
            else:
                raise ValueError("DynamicPVServer.havePV returned an invalid value")
            if O is self.rejectPV:
                self.__addCache(K)
        except:
            self.__addCache(K)
            search.disclaim()
            raise

    def connectPV(self, request):

        try:
            rec, fld, extra = splitPVName(request.pv)
            request.__name = (rec, fld, extra)
        except InvalidPVNameError:
            request.disclaim()
            return

        L.debug('Connect %s'%request.pv)
        
        try:
            O = self.needPV(rec, fld, extra, request)
        except:
            request.disclaim()
            raise
            
        if IPVDBR.implements(O):
            request.claim(O)
        elif O is None:
            request.disclaim()
            return
        else:
            raise ValueError("DynamicPVServer.needPV returned an invalid value")


    def buildChannel(self, request, PV):
        name, extra = request.__name
        L.debug('Create channel to %s'%name)

        chan = Channel(request, PV)
        chan.options = extra

        return chan

    def __addCache(self, k):
        F = len(self.__nak_cache)==0
        self.__nak_cache.add(k)
        if F and not self.__clean:
            self.__clean = self.reactor.callLater(self.cacheCleanPeriod, self.__cleanup)

    def __cleanup(self):
        self.__clean = None
        self.clear()
