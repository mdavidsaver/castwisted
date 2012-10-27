# -*- coding: utf-8 -*-

from TwCAS import dbr

from twisted.trial import unittest

class MockData(object):
    pass

class TestEncode(unittest.TestCase):
    def test_plain(self):
        for N in range(7):
            self.assertEqual('', dbr.metaEncode(N, object()))

    def test_sts(self):
        expect = '\x12\x34\x14\x32'
        padding = {11:1, 13:4}
        for N in range(7,14):
            M = MockData()
            M.status = 0x1234
            M.severity = 0x1432
            
            pad = '\0'*padding.get(N, 0)
            self.assertEqual(expect+pad, dbr.metaEncode(N, M))

    def test_time(self):
        expect = '\x12\x34\x14\x32' + '\x87\x65\x43\x21' + '\0\x10\x01\0'
        padding = {15:2, 18:3, 20:4}
        for N in range(14,21):
            M = MockData()
            M.status = 0x1234
            M.severity = 0x1432
            M.timestamp = (0x87654321, 0x00100100)
            
            pad = '\0'*padding.get(N, 0)
            self.assertEqual(expect+pad, dbr.metaEncode(N, M))

class TestDecode(unittest.TestCase):
    def test_plain(self):
        for N in range(7):
            O = object() # can't assign to this
            dbr.metaDecode(N, '', O)

    def test_sts(self):
        input = '\x12\x34\x14\x32'
        padding = {11:1, 13:4}
        for N in range(7,14):
            pad = '\0'*padding.get(N, 0)
            D = MockData()
            dbr.metaDecode(N, input+pad, D)
            self.assertEqual(0x1234, D.status)
            self.assertEqual(0x1432, D.severity)

    def test_time(self):
        input = '\x12\x34\x14\x32' + '\x87\x65\x43\x21' + '\0\x10\x01\0'
        padding = {15:2, 18:3, 20:4}
        for N in range(14,21):
            pad = '\0'*padding.get(N, 0)
            D = MockData()
            dbr.metaDecode(N, input+pad, D)
            self.assertEqual(0x1234, D.status)
            self.assertEqual(0x1432, D.severity)
            self.assertEqual((0x87654321, 0x00100100), D.timestamp)
