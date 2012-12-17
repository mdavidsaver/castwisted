# -*- coding: utf-8 -*-

import logging
L = logging.getLogger('TwCAS.plugins.basicvalidator')

from zope.interface import implements

from TwCAS.util.interface import IMailboxValidator
from TwCAS.util.mailbox import BasicValidatorFactory

from TwCAS import dbr
from TwCAS.dbr.defs import string2DBF, DBF

class CommonValidator(object):
    implements(IMailboxValidator)

    def __init__(self, name, config):
        self.name, self.config = name, config

        dbf = string2DBF(config.get(name, 'dbf'))
        self.nativeDBF = self.putDBF = dbf

        if config.has_option(name, 'maxCount'):
            self.maxCount = config.getint(name, 'maxCount')
        else:
            self.maxCount = 1

        self.rights = 3
        if config.has_option(name, 'rw'):
            if not config.getbool(name, 'rw'):
                self.rights = 1

        if config.has_option(name, 'VAL'):
            #TODO: make this work for string array with quoting
            IV = config.get(name, 'VAL').split(',')

        elif dbf==DBF.STRING:
            IV = ['']

        else:
            IV = ['0']
        IV = dbr.valueMake(dbr.DBF.STRING, IV)

        M = dbr.DBRMeta() # dummy for conversion
        IV, M = dbr.castDBR(dbf, dbr.DBF.STRING, IV, M)
        self.IV = IV


    def setup(self):
        return (self.nativeDBF, self.IV, None)
    def put(self,(dbf, value, meta), reply=None, chan=None):
        return (dbf, value, meta)

class NullValidator(CommonValidator):
    pass
nullfactory = BasicValidatorFactory('default', NullValidator)

_num_meta_parts = {
 'HOPR':'upper_disp_limit',
 'LOPR':'lower_disp_limit',
 'HIHI':'upper_alarm_limit',
 'HIGH':'upper_warning_limit',
 'LOW':'lower_warning_limit',
 'LOLO':'lower_alarm_limit'
}
_lim_sevr = ['HHSV', 'HSV', 'LSV', 'LLSV']

class NumericValidator(CommonValidator):
    def __init__(self, name, config):
        super(NumericValidator, self).__init__(name, config)

        if self.nativeDBF in [dbr.DBF.STRING, dbr.DBF.ENUM]:
            raise RuntimeError("%s: numeric validator requires numeric dbf"%name)

    def setup(self):
        dbf, IV, M = super(NumericValidator, self).setup()
        if M is None:
            M = dbr.DBRMeta()

        if self.config.has_option(self.name, 'EGU'):
            M.units = self.config.get(self.name, 'EGU')
        if self.config.has_option(self.name, 'PREC'):
            M.precision = self.config.getint(self.name, 'PREC')

        conv = int
        if dbf in [dbr.DBF.FLOAT, dbr.DBF.DOUBLE]:
            conv = float

        for c,m in _num_meta_parts.iteritems():
            if not self.config.has_option(self.name, c):
                continue
            val = self.config.get(self.name, c)

            setattr(M, m, conv(val))

        for L in _lim_sevr:
            if self.config.has_option(self.name, L):
                setattr(self, L.lower(), int(self.config.get(self.name, L)))
            else:
                setattr(self, L.lower(), 0)

        return (dbf, IV, M)

    def put(self,(dbf, value, meta), reply=None, chan=None):

        if self.hhsv and value[0] >= self.pv.upper_alarm_limit:
            meta.severity = self.hhsv
            meta.status = 3 # HIHI
        elif self.llsv and value[0] <= self.pv.lower_alarm_limit:
            meta.severity = self.llsv
            meta.status = 5 # LOLO
        if self.hsv and value[0] >= self.pv.upper_warning_limit:
            meta.severity = self.hsv
            meta.status = 4 # HIGH
        elif self.lsv and value[0] <= self.pv.lower_warning_limit:
            meta.severity = self.lsv
            meta.status = 6 # LOW
        else:
            meta.severity = meta.status = 0

        return (dbf, value, meta)

numericfactory = BasicValidatorFactory('numeric', NumericValidator)
