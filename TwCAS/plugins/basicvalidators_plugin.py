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

    def __init__(self, config):
        self.config = config

        dbf = string2DBF(config['dbf'])
        self.nativeDBF = self.putDBF = dbf

        self.maxCount = int(config.get('maxCount', '1'))

        self.rights = 3
        if config.getbool('rw', False):
            self.rights = 1

        if 'VAL' in config:
            #TODO: make this work for string array with quoting
            IV = config['VAL'].split(',')

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
    def __init__(self, config):
        super(NumericValidator, self).__init__(config)

        if self.nativeDBF in [dbr.DBF.STRING, dbr.DBF.ENUM]:
            raise RuntimeError("numeric validator requires numeric dbf")

    def setup(self):
        dbf, IV, M = super(NumericValidator, self).setup()
        if M is None:
            M = dbr.DBRMeta()

        if 'EGU' in self.config:
            M.units = self.config['EGU']
        if 'PREC' in self.config:
            M.precision = self.config['PREC']

        conv = int
        if dbf in [dbr.DBF.FLOAT, dbr.DBF.DOUBLE]:
            conv = float

        for c,m in _num_meta_parts.iteritems():
            if c not in self.config:
                continue
            val = self.config[c]

            setattr(M, m, conv(val))

        for L in _lim_sevr:
            setattr(self, L.lower(), int(self.config.get(L, '0')))

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
