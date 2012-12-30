# -*- coding: utf-8 -*-

import logging
L = logging.getLogger('TwCAS.service')

import weakref, time

from TwCAS.dbr.xcodeValue import np

from zope.interface import Interface, Attribute, implements

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.plugin import IPlugin, getPlugins

from TwCAS.interface import IPVDBR
from TwCAS.util.interface import IMailbox, IMailboxValidatorFactory

import TwCAS.plugins as _plugins

from TwCAS import ECA
from TwCAS import dbr as DBR
from TwCAS.dbr.defs import POSIX_TIME_AT_EPICS_EPOCH

__all__ = [
    'DefaultService',
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

class DefaultService(object):
    """Proxy access to the static configuration
    """
    session = None
    def __init__(self, config, name):
        self._name = name
        self._config = config
    def get(self, key, default):
        if self._config.has_option(self._name, key):
            return self._config.get(self._name, key)
        else:
            return default
    def getboolean(self, key, default):
        if self._config.has_option(self._name, key):
            return self._config.getboolean(self._name, key)
        else:
            return default
    def getfloat(self, key, default):
        if self._config.has_option(self._name, key):
            return self._config.getfloat(self._name, key)
        else:
            return default
    def getint(self, key, default):
        if self._config.has_option(self._name, key):
            return self._config.getint(self._name, key)
        else:
            return default

class SessionBase(object):
    implements(IServiceSession, IPlugin)
    
    service = DefaultService

    def __init__(self, service=None, channel=None, options=''):
        self._channel = weakref.ref(channel, self._disconnect)
        self.service = service
        self.options = options
        
        self.subscriptions = weakref.WeakKeyDictionary()

    def getInfo(self):
        # default gives type LONG, but inhibits reads and writes
        L.error("getInfo not implemented")
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

    def put(dtype, dcount, dbrdata, reply=None, chan=None):
        if reply:
            reply.error(ECA.ECA_PUTFAIL)
        L.error("Put not implemented")

    def putAlarm(self, ackt=None, acks=None, reply=None, chan=None):
        pass

    def get(self, request):
        L.error('Get not implemented')
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

    def __init__(self, config, name):
        factoryname = config.get(name, 'service')
        
        for F in getPlugins(IServiceFactory, _plugins):
            if F.name == factoryname:
                break
        else:
            raise KeyError("Unknown service '%s'"%factoryname)

        self.service = F.build(config, name)

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

    def build(config, name):
        """Build a new validator instance.
        
        config - An instance of ConfigParser.SafeConfigParser
        name   - The section name to use for this instance
        
        Returns a instance implementing IDBRPV
        """


class ServiceFactory(object):
    implements(IServiceFactory, IPlugin)
    def __init__(self, name, session):
        self.name, self.session = name, session
    def build(self, config, name):
        service = getattr(self.session, 'service', DefaultService)
        service = service(config, name)
        service.session = self.session
        return service
