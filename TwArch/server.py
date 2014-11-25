# -*- coding: utf-8 -*-

import logging
_log = logging.getLogger(__name__)

from urlparse import parse_qs

import weakref
from twisted.internet import reactor, defer

from zope.interface import implements

from TwCAS.protocol.interface import INameServer, IPVServer, IPVDBR

from collections import defaultdict

from TwCAS.protocol.channel import Channel
from TwCAS.util import splitPVName, InvalidPVNameError

from carchive._conf import loadConfig
from carchive.archive import getArchive

from .pv import PV

class ArchiveServer(object):
    """Serves from a pre-defined list of PVs
    
    Handles tracking of channels.
    """
    implements(INameServer, IPVServer)

    searching = object()

    def __init__(self, key):
        conf = loadConfig(key)
        self.server, self.archs = None, ['*/Current', '*/2014']
        self.pvs = {}
        self._attach(conf)

    @defer.inlineCallbacks
    def _attach(self, conf):
        try:
            self.server = yield getArchive(conf)
        except:
            _log.exception('Failed to attach archive')
            reactor.stop()

    def _getname(self, name):
        rec, fld, extra = splitPVName(name)
        rec = rec[5:] # strip 'hist:'
        if fld:
            rec = '%s.%s'%(rec,fld)
        return rec, parse_qs(extra)

    @defer.inlineCallbacks
    def _search(self, name):
        result = yield self.server.search(exact=name, archs=self.archs,
                                          breakDown=True, rawTime=True)

        assert name in result
        self.pvs.update(result)

    def lookupPV(self, search):
        if self.server is None or not search.pv.startswith('hist:'):
            search.disclaim()

        rec, _ = self._getname(search.pv)
        if len(rec)<4:
            search.disclaim()

        result = self.pvs.get(rec)
        if result is None:
            _log.info('Someone is looking for %s', rec)
            self._search(rec)
            self.pvs[rec] = self.searching
        elif result is not self.searching:
            search.claim()
            return
        search.disclaim()

    def connectPV(self, search):
        if self.server is None or not search.pv.startswith('hist:'):
            search.disclaim()

        rec, extra = self._getname(search.pv)
        if len(rec)<4:
            search.disclaim()

        result = self.pvs.get(rec)
        if result in [None, self.searching]:
            search.disclaim()

        try:
            search.claim(PV(self, result,rec,extra))
        except:
            search.disclaim()
            raise

    def buildChannel(self, request, PV):
        return Channel(request, PV, pvname=PV.name)
