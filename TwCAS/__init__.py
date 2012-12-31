# -*- coding: utf-8 -*-

import logging
from logging import getLogger

__version__ = 'pre1'

if not hasattr(logging, 'NullHandler'):
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass
else:
    from logging import NullHandler

__h=NullHandler()
getLogger("TwCAS").addHandler(__h)

class PrefixLogger(object):
    """A wrapper around a logger object
    which adds a prefix string to all messages
    """
    def __init__(self, logger, obj):
        self._logger, self._obj = logger, obj
    def log(self, lvl, msg, *args, **kws):
        if self._logger.isEnabledFor(lvl):
            msg = "%s: %s"%(self._obj, msg)
            self._logger.log(lvl, msg, *args, **kws)
    def debug(self, msg, *args, **kws):
        self.log(logging.DEBUG, msg, *args, **kws)
    def info(self, msg, *args, **kws):
        self.log(logging.INFO, msg, *args, **kws)
    def warning(self, msg, *args, **kws):
        self.log(logging.WARN, msg, *args, **kws)
    def error(self, msg, *args, **kws):
        self.log(logging.ERROR, msg, *args, **kws)
    def critical(self, msg, *args, **kws):
        self.log(logging.CRITICAL, msg, *args, **kws)
        
    def exception(self, msg, *args):
        self.error(*((msg,) + args), **{'exc_info': 1})
