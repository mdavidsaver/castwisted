# -*- coding: utf-8 -*-
"""
Created on Sun Jul 29 11:23:26 2012

@author: mdavidsaver
"""

from zope.interface import Interface, Attribute

class INameServer(Interface):
    def lookupPV(search):
        """Called for each PV search request received by a server.

        The argument is an instance of @PVSearch which should
        be used to answer the query.

        Queries should be answered as soon as possible or dropped.
        Clients typically timeout on a particular search request quickly.
        """

class IPVServer(Interface):
    def connectPV(request):
        """Called to initiate a request for a channel to a PV
        
        The argument is an instance of @PVConnect which should
        be used to answer the query.

        Queries should be answered as soon as possible or dropped.
        Clients typically timeout on a particular connect request quickly.
        """

    def buildChannel(request, PV):
        """Called when a request is claimed to create a new channel object.
        
        Returns an object implementing IChannel
        """

class ICircuit(Interface):
    def write(data):
        """Send data to peer
        """

    def dropChannel(chan):
        """Remove all references to a channel.
        
        Sends disconnect message to peer if circuit is active.
        """

class IChannel(Interface):

    sid = Attribute("Server ID associated with this channel")
    cid = Attribute("Client ID associated with this channel")
    client = Attribute("Client requesting this channel tuple(Host,Port)")
    clientVersion = Attribute("Protocol version used by this client")

    def channelClosed():
        """Channel closed by peer.
        
        Note that one cause of this is TCP connection loss.
        """

    def messageReceived(cmd, dtype, dcount, p1, p2, payload):
        """A CA message for this channel has been received
        """

    def write(data):
        """Send data on the circuit
        """

    def getCircuit():
        """Return the @CASTCP behind this channel
        """

class IPV(Interface):
    
    def getInfo():
        """Fetch channel information.
        
        Succesive calls are allowed to return different results.
        
        Returns (native_dbr, maxcount, rights)
        """

class IPVRequest(Interface):
    """For requests involving a PV (lookup or channel create)
    """
    pv = Attribute("PV name string")
    sid = Attribute("Server ID associated with this operation")
    cid = Attribute("Client ID associated with this operation")
    client = Attribute("Client requesting this operation tuple(Host,Port)")
    clientVersion = Attribute("Protocol version used by this client")

    replied = Attribute("Reply to request has been sent")
