# -*- coding: utf-8 -*-
"""
Created on Sun Jul 29 10:34:57 2012

@author: mdavidsaver
"""

from struct import Struct
import socket

class CAProtoFault(RuntimeError):
    """Unrecoverable protocol error
    """

class CAException(RuntimeError):
    """Fail the operation by sending an exception to the client.
    
    Thrown during processing of a received message to signal a failure of the
    operation which does not close the channel or the TCP connection.
    """
    def __init__(self, status, msg):
        self.eca = status
        RuntimeError.__init__(self, msg)

VERSION = 13

# Short header
caheader = Struct('!HHHHII')

assert caheader.size==16

# Extended header for large payload
caheaderext = Struct('!II')

assert caheaderext.size==8

# Full header for large payloads
caheaderlarge = Struct('!HHHHIIII')

assert caheaderlarge.size==24


# payload for search responce
casearchreply = Struct('!HHHHIIHxxxxxx')

assert casearchreply.size==24

casubscript = Struct('!xxxxxxxxxxxxHxx')

assert casubscript.size==16

def pad(blen):
    """Returns a string with enough padding for the message of the given length
    """
    return '\0'*((8-(blen%8))&7)

def padMsg(msg):
    return msg + pad(len(msg))

__ipaddr = Struct('!I')
def addr2int(addr):
    I, = __ipaddr.unpack(socket.inet_aton(addr))
    return I
