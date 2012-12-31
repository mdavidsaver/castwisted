# -*- coding: utf-8 -*-


from zope.interface import implements
from twisted.internet.interfaces import IConsumer, IPushProducer
from twisted.internet.defer import Deferred, succeed
from twisted.internet.protocol import connectionDone

__all__ = ['MuxProducer']

class MuxConsumer(object):
    """Individual producers are given a unique consumer to use.
    """
    implements(IConsumer)

    def __init__(self, writer):
        self.__writer = writer
        self.producer = None
        self.stream = False

        self.write = self.__writer.write

    def registerProducer(self, producer, streaming):
        assert self.producer is None, "Producer already registered"
        assert streaming, "Only streaming producers supported"
        assert IPushProducer.providedBy(producer)
        self.producer = producer
        self.stream = streaming
        self.__writer._consumers.append(self)

    def unregisterProducer(self):
        assert self.producer is not None, "No Producer registered"
        self.producer = None
        self.__writer._consumers.remove(self)

class MuxProducer(object):
    """
    An adapter to support many producers wishing to
    write data to a single consumer.  This adapter
    handles broadcasting notifications from the underlying
    consumer to all producers
    """
    implements(IPushProducer)

    def __init__(self, consumer):
        self._consumers = []
        self._waiters = []
        self._paused = False
        self.consumer = consumer
        self.consumer.registerProducer(self, True)

        self.write = self.consumer.write

    @property
    def paused(self):
        return self._paused

    def stopProducing(self):
        assert self.consumer
        C, self.consumer = self.consumer, None
        self._write = lambda:None
        C.unregisterProducer()
        for W in self._waiters:
            W.errback(connectionDone)
        for C in self._consumers:
            C.producer.stopProducing()

        self._waiters = []
        self.write = lambda X:None

    def getConsumer(self):
        assert self.consumer is not None
        return MuxConsumer(self)

    def getWaiter(self):
        """Return a deferred which will fire
        the next time sending is possible
        """
        assert self.consumer is not None
        if not self._paused:
            return succeed(self.consumer)
        D = Deferred(self._cancelWaiter)
        self._waiters.append(D)
        return D

    def _cancelWaiter(self, D):
        self._waiters.remove(D)

    def resumeProducing(self):
        if not self._paused:
            return
        self._paused = False
        Ws, self._waiters = self._waiters, []
        for W in Ws:
            W.callback(self.consumer)
        for C in self._consumers:
            C.producer.resumeProducing()

    def pauseProducing(self):
        if self._paused:
            return
        self._paused = True
        for C in self._consumers:
            C.producer.pauseProducing()
