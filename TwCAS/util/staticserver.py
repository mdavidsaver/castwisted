# -*- coding: utf-8 -*-

import logging
L = logging.getLogger('TwCAS.staticserver')

import weakref

from zope.interface import implements

from TwCAS.interface import INameServer, IPVServer, IPVDBR

from collections import defaultdict

from TwCAS.channel import Channel
from TwCAS.util import splitPVName, InvalidPVNameError

class StaticPVServer(object):
    """Serves from a pre-defined list of PVs
    
    Handles tracking of channels.
    """
    implements(INameServer, IPVServer)

    def __init__(self):
        self._pvs = {}

        # Maps PV name to a list of channels
        self._channels = defaultdict(weakref.WeakKeyDictionary)

    def add(self, name, PV):
        """Add a new PV to the server
        """
        assert IPVDBR.providedBy(PV)
        if name in self._pvs:
            raise RuntimeError("A PV named '%s' is already present"%name)

        self._pvs[name] = PV

    def remove(self, obj):
        """Remove a PV from the server.
        
        This causes any channels open to this PV
        to be closed.
        """
        if IPVDBR.providedBy(obj):
            v = None
            for n,v in self._pvs.iteritems():
                if v is obj:
                    break
            if v is not obj:
                raise ValueError('PV object not found')
            self._pvs.pop(n)
        else:
            v = self._pvs[obj]
            n = obj

        chans = self._channels.pop(n)
        for C in chans.keys():
            chans.close()

    def lookupPV(self, search):
        try:
            rec, fld, extra = splitPVName(search.pv)
            name = '%s.%s'%(rec,fld or 'VAL')
        except InvalidPVNameError:
            search.disclaim()
            return
        L.debug('Lookup %s'%name)
        if name in self._pvs:
            search.claim()
        else:
            search.disclaim()

    def connectPV(self, request):
        try:
            rec, fld, extra = splitPVName(request.pv)
            name = '%s.%s'%(rec,fld or 'VAL')
        except InvalidPVNameError:
            request.disclaim()
            return
        L.debug('Connect %s'%name)
        pv = self._pvs.get(name, None)
        if pv is None:
            request.disclaim()
            return

        request.__name = (name,extra)
        request.claim(pv)

    def buildChannel(self, request, PV):
        name, extra = request.__name
        L.debug('Create channel to %s'%name)

        chan = Channel(request, PV)
        chan.options = extra

        self._channels[name][chan]=None
        return chan
