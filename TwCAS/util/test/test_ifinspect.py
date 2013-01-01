# -*- coding: utf-8 -*-

import logging
logging.basicConfig(level=logging.DEBUG)

from twisted.trial import unittest

from TwCAS.util.ifinspect import getifinfo

class TestIfInfo(unittest.TestCase):
    def test_get(self):
        IF = getifinfo()

        self.assertTrue(len(IF)>=1)

    def test_lo(self):
        for IF in getifinfo():
            if IF.loopback:
                self.assertTrue(True)
                break
        else:
            self.assertTrue(False, msg="Missing loopback")
