# Copyright (C) 2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import unittest

from nose.tools import istest

from swh.deposit import utils


class UtilsTestCase(unittest.TestCase):
    """Utils library

    """
    @istest
    def convert(self):
        d0 = {
            'author': 'someone',
            'a': 1
        }

        d1 = {
            'author': ['author0', 'author1'],
            'b': {
                '1': '2'
            }
        }

        d2 = {
            'author': 'else',
        }

        actual_merge = utils.merge([d0, d1, d2])

        expected_merge = {
            'a': 1,
            'author': ['someone', 'author0', 'author1', 'else'],
            'b': {
                '1': '2'
            }
        }
        self.assertEquals(actual_merge, expected_merge)
