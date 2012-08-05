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
    
    dbr = Attribute("Native DBR type")
    maxCount = Attribute("Max number of elements")
    rights = Attribute("Permissions mask")

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

    def getPeer():
        """Returns the IP4Address of the client
        """

    def getCircuit():
        """Return the @MuxProducer behind this channel
        """

class IPVDBR(Interface):
    """Interface used to move DBR data to and from a PV.
    """
    
    def getInfo(request):
        """Fetch channel information.
        
        The argument is an instance of @PVConnect which may to determine
        the result.
        
        Succesive calls are allowed to return different results.
        
        Returns (native_dbr, maxcount, rights)
        """

    def put(dtype, dcount, dbrdata, reply=None):
        """Called when a put request is received.
        
        If the client requests completion notification then
        the reply argument will be a @PutNotify instance.
        """

    def get(reply):
        """Called when a get request is received.
        
        The reply argument will be a @GetNotify instance used to communicate
        the result to the client.
        """

    def monitor(reply):
        """Called when a get request is received.
        
        The reply argument will be a @Subscription instance used to communicate
        the results to the client.
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
