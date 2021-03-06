# -*- coding: utf-8 -*-

import logging
L = logging.getLogger('TwCAS.service.core')

import weakref

from zope.interface import Interface, Attribute, implements

from twisted.plugin import IPlugin, getPlugins

from TwCAS.protocol.interface import IPVDBR

import TwCAS.plugins as _plugins

from TwCAS.protocol import ECA
from TwCAS import dbr as DBR

__all__ = [
    'IServiceSession',
    'SessionBase',
    'ServiceFactory',
]

class IServiceSession(IPVDBR):
    name = Attribute("Name string for this service")    
    
    service = Attribute("""The service state class
    
    This class will be instanciated for each service PV
    with access to the configuration for that PV.
    This instance will later be passed to all
    session instances.
    """)
    
    def __init__(service=None, channel=None, options=''):
        """A new session is being opened.
        
        The session must not keep a strong reference
        to the channel!
        """

    def getInfo():
        """Provide information on native channel type
        Return value is the same as IPVDBR.getInfo()
        
        Unlike IPVDBR.getInfo(), this method will only
        be called once.
        """

class SessionBase(object):
    implements(IServiceSession, IPlugin)
    
    service = None

    def __init__(self, service=None, channel=None, options=''):
        self._channel = weakref.ref(channel, self._disconnect)
        self.service = service
        self.options = options
        
        self.subscriptions = weakref.WeakKeyDictionary()

    def getInfo(self):
        # default gives type LONG, but inhibits reads and writes
        L.error("getInfo not implemented by %s", self.__class__.__name__)
        return (DBR.DBF.LONG, 1, 0)

    def _disconnect(self, _):
        self.disconnect()
    def disconnect(self):
        """Called when this session's channel is lost
        """
        self.subscriptions = None

    @property
    def channel(self):
        return self._channel()

    def put(self,dtype, dcount, dbrdata, reply=None, chan=None):
        if reply:
            reply.error(ECA.ECA_PUTFAIL)
        L.error("Put not implemented by %s", self.__class__.__name__)

    def putAlarm(self, ackt=None, acks=None, reply=None, chan=None):
        if reply:
            reply.error(ECA.ECA_PUTFAIL)

    def get(self, request):
        L.error('Get not implemented by %s', self.__class__.__name__)
        request.error(ECA.ECA_GETFAIL)

    def monitor(self, request):
        self.get(request)
        if request.complete:
            return
        self.subscriptions[request] = None

    def post(self, mask=DBR.DBE.VALUE|DBR.DBE.ARCHIVE):
        for M in self.subscriptions.keys():
            if M.mask&mask:
                self.get(M)
        

class ServicePV(object):
    """A PV which has no global state.
    
    Each client gets a unique view
    """
    implements(IPVDBR)

    def __init__(self, config):
        factoryname = config['service']
        
        for F in getPlugins(IServiceFactory, _plugins):
            if F.name == factoryname:
                break
        else:
            raise KeyError("Unknown service '%s'"%factoryname)

        self.service = F.build(config)

    def getInfo(self, request):
        Sklass = self.service.session
        S = Sklass(self, request.channel,
                   getattr(request, 'options', ''))

        # retarget future CA operations to the session
        request.channel.pv = S

        return S.getInfo()

class IServiceFactory(Interface):
    """Builds a IServiceSession using configuration from ConfigParser
    """

    name = Attribute("The unique name this factory is known by")

    def build(config):
        """Build a new validator instance.
        
        config - Dictionary of config parameters
        
        Returns a instance implementing IDBRPV
        """


class ServiceFactory(object):
    implements(IServiceFactory, IPlugin)
    def __init__(self, name, session):
        self.name, self.session = name, session
    def build(self, config):
        service = getattr(self.session, 'service', None)
        service = service(config) if service else config
        service.session = self.session
        return service
