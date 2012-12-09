# -*- coding: utf-8 -*-

from TwCAS import dbr
from TwCAS.dbr.defs import DBF, DBRMeta
from TwCAS.dbr.convert import castDBR

from twisted.trial import unittest

class TestConvert(unittest.TestCase):
    def makeMeta(self, mval):
        meta = DBRMeta()
        for F in dbr.convert._val_metas:
            setattr(meta, F, mval)
        
    def test_passthrough(self):
        """When no conversion is needed
        """
        for N in dbr.defs.allDBR:
            A, B = object(), object()
            C, D = castDBR(N, N, A, B)
            self.assertIdentical(A, C)
            self.assertIdentical(B, D)

    def test_trival(self):
        """When both DBR types have the same Python type
        """
        for R in [(DBF.CHAR, DBF.SHORT, DBF.LONG),
                  (DBF.FLOAT, DBF.DOUBLE)]:

            for N in R:
                for M in R:
                    if M==N:
                        continue
            A, B = object(), object()
            C, D = castDBR(M, N, A, B)
            self.assertIdentical(A, C)
            self.assertIdentical(B, D)

    def test_int2float(self):
        ival = dbr.valueMake(DBF.LONG, [5])
        imeta = self.makeMeta(42)
        fval, fmeta = castDBR(DBF.DOUBLE, DBF.LONG, ival, imeta)
        self.assertTrue(isinstance(fval[0], float))
        for F in dbr.convert._val_metas:
            self.assertTrue(isinstance(getattr(fmeta, F), float))

    def test_float2int(self):
        ival = dbr.valueMake(DBF.DOUBLE, [5.1])
        imeta = self.makeMeta(4.2)
        fval, fmeta = castDBR(DBF.LONG, DBF.DOUBLE, ival, imeta)
        self.assertTrue(isinstance(fval[0], int))
        for F in dbr.convert._val_metas:
            self.assertTrue(isinstance(getattr(fmeta, F), int))

    def test_float2str(self):
        ival = dbr.valueMake(DBF.DOUBLE, [5.1])
        imeta = self.makeMeta(4.2)
        fval, fmeta = castDBR(DBF.STRING, DBF.DOUBLE, ival, imeta)
        self.assertEqual(fval, [str(5.1)])

    def test_str2float(self):
        ival = [str(5.1)]
        imeta = DBRMeta()
        fval, fmeta = castDBR(DBF.DOUBLE, DBF.STRING, ival, imeta)
        self.assertAlmostEqual(5.1, fval[0])
