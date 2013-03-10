# -*- coding: utf-8 -*-

from ConfigParser import NoOptionError, NoSectionError

class ConfigDict(object):
    """Adapt read access to one section of a ConfigParser.

    Looks like a dictionary
    """

    def __init__(self, conf, name):
        self._conf, self._sec = conf, name

    def __len__(self):
        return len(self.keys())

    def __contains__(self, key):
        try:
            return self._conf.has_option(self, key)
        except NoSectionError:
            return False

    has_key = __contains__

    def __getitem__(self, key):
        try:
            return self._conf.get(self._sec, key)
        except (NoOptionError, NoSectionError):
            raise KeyError(key)

    def __setitem__(self, key, value):
        raise NotImplemented
    def __delitem__(self, key):
        raise NotImplemented

    def get(self, key, default=None):
        try:
            return self._conf.get(self._sec, key)
        except (NoOptionError, NoSectionError):
            return default

    def getboolean(self, key, default=None):
        try:
            return self._conf.getboolean(self._sec, key)
        except (NoOptionError, NoSectionError):
            return default
    getbool = getboolean
    def getint(self, key, default=None):
        try:
            return self._conf.getint(self._sec, key)
        except (NoOptionError, NoSectionError):
            return default
    def getfloat(self, key, default=None):
        try:
            return self._conf.getfloat(self._sec, key)
        except (NoOptionError, NoSectionError):
            return default

    def keys(self):
        try:
            return self._conf.options(self._sec)
        except NoSectionError:
            return []

    def values(self):
        for k in self.keys():
            return self[k]
    def items(self):
        for k in self.keys():
            return (k, self[k])

    def __iter__(self):
        return iter(self.keys())
    def iterkeys(self):
        return iter(self.keys())
    def itervalues(self):
        return iter(self.values())
    def iteritems(self):
        return iter(self.items())
