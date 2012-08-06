# -*- coding: utf-8 -*-

import logging
L = logging.getLogger('TwCAS.staticserver')

from zope.interface import implements

from interface import INameServer, IPVServer, IPVDBR

from collections import defaultdict

from channel import Channel

class StaticPVServer(object):
    """Serves from a pre-defined list of PVs
    
    Handles tracking of channels.
    """
    implements(INameServer, IPVServer)

    def __init__(self):
        self._pvs = {}

        # Maps PV name to a list of channels
        self._channels = defaultdict(list)

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
        for C in chans:
            chans.close()

    def splitPvName(self, name):
        """Process the requested name string to seperate
        out the part identifying the PV.
        
        Returns ('pvname', 'channel options')
        """
        rec, right = name.partition('.')
        if len(right):
            #TODO: Slow
            fld, extra = right, ''
            for I in range(len(right)):
                C = right[I]
                if C>='A' and C<='Z':
                    continue
                # found a seperator
                fld = right[:I]
                extra = right[I:]
        else:
            fld='VAL'
            extra=''

        return ('%s.%s'%(rec,fld), extra)

    def lookupPV(self, search):
        name, extra = self.splitPvName(search.pv)
        if name in self._pvs:
            search.claim()
        else:
            search.disclaim()

    def connectPV(self, request):
        name, extra = self.splitPvName(request.pv)
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

        self._channels[name].append(chan)