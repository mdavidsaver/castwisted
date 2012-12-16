# -*- coding: utf-8 -*-

import logging
L = logging.getLogger('TwCAS.plugins.basicvalidator')

from zope.interface import implements

from TwCAS.util.interface import IMailboxValidator
from TwCAS.util.mailbox import BasicValidatorFactory
from TwCAS.application import SelfFactory
from twisted.plugin import IPlugin

from  TwCAS import dbr
from TwCAS.dbr.defs import string2DBF, DBF

class NullValidator(object):
    implements(IPlugin, IMailboxValidator)

    def __init__(self, name, config):
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

        if config.has_option(name, 'value'):
            #TODO: make this work for string array with quoting
            IV = config.get(name, 'value').split(',')
            
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

nullfactory = BasicValidatorFactory('default', NullValidator)
