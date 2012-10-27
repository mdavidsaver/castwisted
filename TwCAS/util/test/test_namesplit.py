# -*- coding: utf-8 -*-

from twisted.trial import unittest

from TwCAS.util import splitPVName, InvalidPVNameError

class TestNameSplit(unittest.TestCase):
    
    def test_invalid(self):
        for N in [""
                 ,"."
                 ,".FLD"
                 ]:
            try:
                self.assertRaises(InvalidPVNameError, splitPVName, N)
            except:
                print 'Failed on name ',N
                raise

    def test_valid(self):
        for I,E in [("rec",("rec","",""))
                   ,("recORD.FLD",("recORD","FLD",""))
                   ,("recORD.FLD.JUNK",("recORD","FLD",".JUNK"))
                   ,("recORD.FLD$",("recORD","FLD","$"))
                   ,("recORD.FLD[-1]",("recORD","FLD","[-1]"))
                   ]:
            try:
               O = splitPVName(I)
               self.assertEqual(E,O)
            except:
                print 'Failed on name ',I
                raise
