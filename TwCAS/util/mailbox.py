# -*- coding: utf-8 -*-

import logging
L = logging.getLogger('TwCAS.mailbox')

import weakref, time

from TwCAS.dbr.xcodeValue import np

from zope.interface import implements

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.plugin import IPlugin

from TwCAS.interface import IPVDBR
from TwCAS.util.interface import IMailbox, IMailboxValidatorFactory

from TwCAS import ECA
from TwCAS import dbr as DBR
from TwCAS.dbr.defs import POSIX_TIME_AT_EPICS_EPOCH

class MetaDescriptor(object):
    def __init__(self, name, default):
        self.name, self.default = name, default
    def __get__(self, inst, owner):
        return getattr(inst._MailboxPV__meta, self.name, self.default)
    #def __set__(self, inst, value):
    #    setattr(inst._MailboxPV__meta, self.name, value)

class MailboxPV(object):
    """A PV which stores DBR data of a specific type.
    
    Data of other types will be converted if possible.

    Sends monitor updates on value or meta-data change.

    Handles update of meta-data by client.
    """
    implements(IPVDBR,IMailbox)
    longStringSize = 128
    rights = 3
    
    def __init__(self, validator):
        self.validator = validator
        validator.pv = self

        usearray = getattr(validator, 'usearray', None)
        if usearray is False and not np:
            raise RuntimeError("Validator %s requires numpy, but no available",
                               str(self))

        validator.usearray = np is None

        try:
            setup = validator.setup
        except AttributeError:
            IV = None
        else:
            IV = setup()

        if IV is None:
            if validator.nativeDBF==DBR.DBF.STRING:
                initial = ['']
            else:
                initial = [0]
            self.__value = DBR.valueMake(validator.nativeDBF, initial,
                                         usearray = validator.usearray)

            self.dbf = validator.nativeDBF

            self.__meta = None
        else:
            self.dbf, self.__value, self.__meta = IV
            self.__value = DBR.valueMake(self.dbf, self.__value,
                                         usearray = validator.usearray)

        if self.__meta is None:
            self.__meta = DBR.DBRMeta()
            self.__meta.status = 0
            self.__meta.severity = 0
            self.__meta.timestamp = (0,0)

        self.__meta.ackt = getattr(self.__meta, 'ackt', 0)
        self.__meta.acks = 0

        self.events = 0
        self.__subscriptions = weakref.WeakKeyDictionary()
        self.__putQ = []

    def getInfo(self, request):
        V = self.validator
        try:
            dbf, count, rights = V.getInfo()
        except AttributeError:
            dbf, count, rights = V.nativeDBF, V.maxCount, V.rights
            
        longStringSize = getattr(self.validator, 'longStringSize', self.longStringSize)

        if dbf==DBR.DBF.STRING and count==1 and \
                getattr(request, 'options', '')=='$':
            # long string
            return (DBR.DBF.UCHAR, longStringSize, rights)
        else:
            return (dbf, count, rights)

    def get(self, request):
        try:
            request.update(self.value, self.__meta, dbf=self.dbf)

        except ValueError:
            request.error(ECA.ECA_NOCONVERT)
            L.exception("Failed to convert value from DBF %d to DBR %d",
                        self.dbf, request.dbr)

    def monitor(self, request):
        self.get(request)
        if request.complete:
            return
        self.__subscriptions[request] = None

    def putAlarm(self, ackt=None, acks=None, reply=None, chan=None):
        if ackt is not None:
            self.__meta.ackt = 1 if ackt else 0
        elif acks is not None:
            if acks >= getattr(self.__meta, 'acks', 0):
                self.__meta.acks = 0

    def put(self, dtype, dcount, dbrdata, reply=None, chan=None):

        N = getattr(self.validator, 'putQueueLen', 1)
        
        if N==0:
            # No buffering so dispatch synchronously
            self.__putQ = [(dtype, dcount, dbrdata, reply, chan)]
            self._put()

        elif len(self.__putQ) < N:
            if len(self.__putQ)==0:
                reactor.callLater(0, self._put)
            self.__putQ.append((dtype, dcount, dbrdata, reply, chan))

        elif reply: # request dropped
            reply.error(ECA.ECA_PUTFAIL)

    def _put(self):
        dtype, dcount, dbrdata, reply, chan = self.__putQ.pop(0)
        try:
            self._put2(dtype, dcount, dbrdata, reply, chan)
        except:
            # This is intended to catch internal logic errors
            # user errors should be handled by _put2
            if reply:
                reply.error(ECA.ECA_PUTFAIL)
            raise

    def _put2(self, dtype, dcount, dbrdata, reply, chan):
        dbf, metaLen = DBR.dbr_info(dtype)
        
        M = DBR.DBRMeta(udf=None)

        val = DBR.valueDecode(dbf, dbrdata[metaLen:], dcount,
                              forcearray=self.validator.usearray)
        DBR.metaDecode(dtype, dbrdata[:metaLen], M)

        mydbf = getattr(self.validator, 'putDBF', None)
        if mydbf is not None:
            val, M = DBR.castDBR(mydbf, dbf, val, M)

        self.events = DBR.DBE.VALUE | DBR.DBE.ARCHIVE

        try:
            R = self.validator.put((dbf, val, M), reply, chan)
        except:
            if reply:
                reply.error(ECA.ECA_PUTFAIL)
            L.exception("Validator put error")
            M.severity = 3
            M.status = 17 # UDF
            R = (None, val, M)

        if isinstance(R, Deferred):
            # start async action
            R.addCallback(self._putComplete, reply)
            R.addErrback(self._putFail, M, reply)

        else:
            self._putComplete(R, reply)

    def _putFail(self, err, M, reply):
        # TODO: log stack trace
        L.error("Validator async put error")
        M.severity = 3
        M.status = 17 # UDF
        # Update alarm
        self._putComplete((self.dbf, self.value, M), reply)

    def _putComplete(self, (dbf, val, M), reply):
        events = self.events

        self.__value = val

        sevr = self.severity
        nsev = getattr(M, 'severity', sevr)
        stat = self.status
        nsta = getattr(M, 'status', stat)
        
        self.__meta.status = nsta
        self.__meta.severity = nsev
        
        if sevr!=nsev or stat!=nsta:
            events |= DBR.DBE.ALARM
        if not self.__meta.ackt and sevr >= self.__meta.acks:
            self.__meta.acks = sevr

        try:
            self.__meta.timestamp = M.timestamp
        except AttributeError:
            # sender did not include timestamp
            now = time.time()
            self.__meta.timestamp = (int(now)-POSIX_TIME_AT_EPICS_EPOCH,
                                     int((now%1)*1e9))

        # TODO: update GR and CTRL meta data
        
        for M in self.__subscriptions.keys():
            if M.mask&events:
                self.get(M)

        if reply:
            reply.finish()

    # R/O access to value and meta-data
    @property
    def status(self):
        return getattr(self.__meta, 'status', 0)
    @property
    def severity(self):
        return getattr(self.__meta, 'severity', 0)
    @property
    def timestamp(self):
        ts = getattr(self.__meta, 'timestamp', (0,0))
        return float(ts[0]) + 1e-9*ts[1]
    @property
    def value(self):
        return self.__value

    egu = MetaDescriptor('egu', '')
    prec = MetaDescriptor('prec', 0)
    enums = MetaDescriptor('enums', 0)

    upper_disp_limit = MetaDescriptor('upper_disp_limit', 0)
    lower_disp_limit = MetaDescriptor('lower_disp_limit', 0)
    upper_alarm_limit = MetaDescriptor('upper_alarm_limi', 0)
    upper_warning_limit = MetaDescriptor('upper_warning_limit', 0)
    lower_warning_limit = MetaDescriptor('lower_warning_limit', 0)
    lower_alarm_limit = MetaDescriptor('lower_alarm_limit', 0)

class BasicValidatorFactory(object):
    """For PV types which can configure themselves
    """
    implements(IMailboxValidatorFactory, IPlugin)
    def __init__(self, name, pvclass):
        self.name, self.klass = name, pvclass
    def build(self, config, name):
        return self.klass(config, name)
