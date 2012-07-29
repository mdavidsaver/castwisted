# -*- coding: utf-8 -*-
"""
Created on Sun Jul 29 11:23:26 2012

@author: mdavidsaver
"""

from zope.interface import Interface #, Attribute

class INameServer(Interface):
    def lookupPV(search):
        """Called for each PV search request received by a server.

        The argument is an instance of @PVSearch which should
        be used to answer the query.

        Queries should be answered as soon as possible or dropped.
        Clients typicallys timeout on a particular search request quickly.
        """
