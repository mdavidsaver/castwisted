# -*- coding: utf-8 -*-
"""
Testing helpers

@author: mdavidsaver
"""

from twisted.internet.interfaces import IUDPTransport, ITCPTransport, IConsumer
from twisted.internet.address import IPv4Address
from twisted.internet.defer import Deferred, succeed

from zope.interface import implements

from caproto import caheader, caheaderext, caheaderlarge

class TooShort(RuntimeError):
    pass
class InvalidMessage(RuntimeError):
    pass

class TestUDPTransport:
    implements(IUDPTransport)

    def __init__(self, defer=None):
        self.defer = defer or Deferred()

    def connect(self, host, port):
        self.peer = (host, port)

    def stopListening(self):
        self.defer.cancel()
        return succeed(True)

    def write(self, data, dest=None):
        self.defer.callback((data, dest or self.peer))

    def getHost(self):
        return IPv4Address('UDP', '127.0.0.1', 1423)

class TestTCPTransport:
    implements(ITCPTransport, IConsumer)
    disconnecting = False

    def __init__(self):
        self.defer = Deferred()

    def write(self, data):
        D, self.defer = self.defer, Deferred()
        D.callback(data)

    def loseConnection(self):
        self.disconnecting = True
        D, self.defer = self.defer, None
        D.callback(None)

    def getPeer(self):
        return IPv4Address('TCP', '127.0.0.2', 4231)

    def getHost(self):
        return IPv4Address('TCP', '127.0.0.1', 1423)

    def registerProducer(self, producer, stream):
        pass
    
    def unregisterProducer(self):
        pass

def makeCA(cmd, dtype=0, dcount=0, p1=0, p2=0, body=''):
    if len(body)>=0xffff:
        msg = caheaderlarge.pack(cmd, 0xffff, dtype, 0, p1, p2, len(body), dcount)
    else:
        msg = caheader.pack(cmd, len(body), dtype, dcount, p1, p2)
    return msg + str(body)

class TestMsg(object):
    def __init__(self, **kws):
        for k,v in kws.iteritems():
            setattr(self,k,v)

def checkCA(test, data,
            cmd=None, dtype=None, dcount=None, p1=None, p2=None, body=None,
            bodylen=None, hasdbr=False, final=False):
    data = buffer(data)
    if len(data)<caheader.size:
        raise TooShort()
    pcmd, pblen, pdtype, pdcount, pp1, pp2 =caheader.unpack_from(data)

    if cmd is not None:
        test.assertEqual(pcmd, cmd)
    if dtype is not None:
        test.assertEqual(pdtype, dtype)
    if p1 is not None:
        test.assertEqual(pp1, p1)
    if p2 is not None:
        test.assertEqual(pp2, p2)

    test.assertTrue(hasdbr or pblen<0xffff)

    if pblen==0xffff and pdcount==0:
        if len(data)<caheaderlarge.size:
            raise TooShort()
        pblen, pdcount = caheaderext.unpack_from(data, caheader.size)
        pbody = buffer(data, caheaderlarge.size, pblen)
        remainder = buffer(data, caheaderlarge.size + pblen)
    else:
        pbody = buffer(data, caheader.size, pblen)
        remainder = buffer(data, caheader.size + pblen)

    if bodylen is not None:
        test.assertEqual(len(pbody), bodylen)
    if dcount is not None:
        test.assertEqual(pdcount, dcount)
    if body is not None:
        test.assertEqual(str(pbody), body)

    if final:
        test.assertEqual(len(remainder), 0)

    return TestMsg(cmd=pcmd, dtype=pdtype, dcount=pdcount, p1=pp1, p2=pp2, body=pbody), remainder
