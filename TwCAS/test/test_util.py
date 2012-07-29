# -*- coding: utf-8 -*-
"""
Created on Sun Jul 29 13:20:36 2012

@author: mdavidsaver
"""

from twisted.trial import unittest

from TwCAS import caproto, helptest

class TestProto(unittest.TestCase):
    
    def test_pad(self):
        for I in range(64):
            expected = 8 - I%8
            if expected==8:
                expected=0
            self.assertEqual(caproto.pad(I), '\0'*expected)

    def test_addr2int(self):
        self.assertEqual(caproto.addr2int('127.0.0.1'), 0x7f000001)
        self.assertEqual(caproto.addr2int('192.168.5.1'), 0xc0a80501)

class TestHelper(unittest.TestCase):
    
    def test_make(self):
        self.assertEqual(helptest.makeCA(0), '\0'*16)
        
        self.assertEqual(helptest.makeCA(5), '\0\x05' + '\0'*14)

    def test_check(self):
        pkt = helptest.makeCA(6, dtype=1, dcount=2, p1=3, p2=4)
        
        msg, rem = helptest.checkCA(self, pkt, cmd=6, dtype=1, dcount=2, p1=3, p2=4, bodylen=0)

        self.assertEqual(str(rem), '')

        self.assertEqual(msg.cmd, 6)
        self.assertEqual(msg.dtype, 1)
        self.assertEqual(msg.dcount, 2)
        self.assertEqual(msg.p1, 3)
        self.assertEqual(msg.p2, 4)
        self.assertEqual(str(msg.body), '')

    def test_checkfail(self):
        pkt = helptest.makeCA(6, dtype=1, dcount=2, p1=3, p2=4)

        self.assertRaises(helptest.TooShort, helptest.checkCA, self, '\0\0')

        self.assertRaises(unittest.FailTest, helptest.checkCA, self, pkt,
                          cmd=5)
        self.assertRaises(unittest.FailTest, helptest.checkCA, self, pkt,
                          dtype=2)
        self.assertRaises(unittest.FailTest, helptest.checkCA, self, pkt,
                          dcount=3)
        self.assertRaises(unittest.FailTest, helptest.checkCA, self, pkt,
                          p1=4)
        self.assertRaises(unittest.FailTest, helptest.checkCA, self, pkt,
                          p2=5)
