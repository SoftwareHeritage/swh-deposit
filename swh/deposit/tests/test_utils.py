# Copyright (C) 2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import unittest


from swh.deposit import utils


class UtilsTestCase(unittest.TestCase):
    """Utils library

    """
    def test_merge(self):
        """Calling utils.merge on dicts should merge without losing information

        """
        d0 = {
            'author': 'someone',
            'license': [['gpl2']],
            'a': 1
        }

        d1 = {
            'author': ['author0', {'name': 'author1'}],
            'license': [['gpl3']],
            'b': {
                '1': '2'
            }
        }

        d2 = {
            'author': map(lambda x: x, ['else']),
            'license': 'mit',
            'b': {
                '2': '3',
            }
        }

        d3 = {
            'author': (v for v in ['no one']),
        }

        actual_merge = utils.merge(d0, d1, d2, d3)

        expected_merge = {
            'a': 1,
            'license': [['gpl2'], ['gpl3'], 'mit'],
            'author': [
                'someone', 'author0', {'name': 'author1'}, 'else', 'no one'],
            'b': {
                '1': '2',
                '2': '3',
            }
        }
        self.assertEqual(actual_merge, expected_merge)

    def test_merge_2(self):
        d0 = {
            'license': 'gpl2',
            'runtime': {
                'os': 'unix derivative'
            }
        }

        d1 = {
            'license': 'gpl3',
            'runtime': 'GNU/Linux'
        }

        expected = {
            'license': ['gpl2', 'gpl3'],
            'runtime': [
                {
                    'os': 'unix derivative'
                },
                'GNU/Linux'
            ],
        }

        actual = utils.merge(d0, d1)
        self.assertEqual(actual, expected)

    def test_merge_edge_cases(self):
        input_dict = {
            'license': ['gpl2', 'gpl3'],
            'runtime': [
                {
                    'os': 'unix derivative'
                },
                'GNU/Linux'
            ],
        }
        # against empty dict
        actual = utils.merge(input_dict, {})
        self.assertEqual(actual, input_dict)

        # against oneself
        actual = utils.merge(input_dict, input_dict, input_dict)
        self.assertEqual(input_dict, input_dict)

    def test_merge_one_dict(self):
        """Merge one dict should result in the same dict value

        """
        input_and_expected = {'anything': 'really'}
        actual = utils.merge(input_and_expected)
        self.assertEqual(actual, input_and_expected)

    def test_merge_raise(self):
        """Calling utils.merge with any no dict argument should raise

        """
        d0 = {
            'author': 'someone',
            'a': 1
        }

        d1 = ['not a dict']

        with self.assertRaises(ValueError):
            utils.merge(d0, d1)

        with self.assertRaises(ValueError):
            utils.merge(d1, d0)

        with self.assertRaises(ValueError):
            utils.merge(d1)

        self.assertEqual(utils.merge(d0), d0)
