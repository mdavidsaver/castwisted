# -*- coding: utf-8 -*-

from twisted.internet.protocol import DatagramProtocol

from TwCAS import getLogger, PrefixLogger
L = getLogger(__name__)

class RepeaterClient(DatagramProtocol):
    
    def __init__(self, port):
        self.ep = ('', port)

    def startProtocol(self):
        self.transport.write('', self.ep)

    def datagramReceived(self, msg, src):

        L.info('%s: %s',src,repr(msg))


if __name__=='__main__':
    from twisted.internet import reactor
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    P = reactor.listenUDP(0, RepeaterClient(5065),
                          interface='127.0.0.1')

    reactor.run()
