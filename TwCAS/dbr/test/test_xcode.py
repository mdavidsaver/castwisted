# -*- coding: utf-8 -*-

from TwCAS import dbr
from TwCAS.dbr import DBF

import array
try:
    import numpy as np
except ImportError:
    np = None

from twisted.trial import unittest

class MockData(object):
    pass

class TestEncodeMeta(unittest.TestCase):
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

class TestDecodeMeta(unittest.TestCase):
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

testdata = [
            (DBF.SHORT,[0x1234],'\x12\x34'),
            (DBF.SHORT,[0x1234, 0x1020],'\x12\x34\x10\x20'),
            (DBF.CHAR ,[0x42, 0x15, 0x17],'\x42\x15\x17'),
            (DBF.STRING,['hello','world'], 'hello'+'\0'*35+'world'+'\0'*35),
            (DBF.STRING,['hello','world',''], 'hello'+'\0'*35+'world'+'\0'*75)
           ]

class TestEncodeValue(unittest.TestCase):

    def test_list(self):
        for dbf, INP, expect in testdata:
            try:
                actual = dbr.valueEncode(dbf, INP)
                self.assertEqual(expect, actual)
            except:
                print 'Failed on',dbf,INP,expect
                raise

    def test_array(self):
        for dbf, INP, expect in testdata:
            try:
                typecode = dbr.xcodeValue._arr_type[dbf]
                if typecode: # false for DBF.STRING
                    INP = array.array(typecode, INP)
                actual = dbr.valueEncode(dbf, INP)
                self.assertEqual(expect, actual)
            except:
                print 'Failed on',dbf,INP,expect
                raise

    if np:
        def test_ndarray(self):
            for dbf, INP, expect in testdata:
                try:
                    dtype = dbr.xcodeValue._host_dtype[dbf]
                    INP = np.asarray(INP, dtype=dtype)
                    actual = dbr.valueEncode(dbf, INP)
                    self.assertEqual(expect, actual)
                except:
                    print 'Failed on',dbf,INP,expect
                    raise
    

class TestDecodeValue(unittest.TestCase):
    def test_array(self):
        for dbf, expect, INP in testdata:
            try:
                typecode = dbr.xcodeValue._arr_type[dbf]
                if typecode: # false for DBF.STRING
                    expect = array.array(typecode, expect)

                actual = dbr.valueDecode(dbf, INP, forcearray=True)
                self.assertEqual(len(expect), len(actual))
                self.assertEqual(expect, actual)
            except:
                print 'Failed on',dbf,INP,expect
                raise

    if np:
        def test_ndarray(self):
            for dbf, expect, INP in testdata:
                try:
                    dtype = dbr.xcodeValue._host_dtype[dbf]
                    expect = np.asarray(expect, dtype=dtype)

                    actual = dbr.valueDecode(dbf, INP)
                    self.assertEqual(len(expect), len(actual))
                    self.assertTrue(np.all(expect==actual))
                except:
                    print 'Failed on',dbf,INP,expect
                    raise
