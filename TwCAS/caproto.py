# -*- coding: utf-8 -*-
"""
Created on Sun Jul 29 10:34:57 2012

@author: mdavidsaver
"""

from struct import Struct

VERSION = 10

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

def pad(blen):
    """Returns a string with enough padding for the message of the given length
    """
    return '\0'*(8-((blen%8)&7))

def padMsg(msg):
    return msg + pad(len(msg))
