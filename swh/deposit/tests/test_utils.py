# Copyright (C) 2018-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import unittest
import pytest

from unittest.mock import patch

from swh.deposit import utils
from swh.deposit.models import Deposit, DepositClient


def test_origin_url_from():
    """With correctly setup-ed deposit, all is fine

    """
    for provider_url, external_id in (
            ('http://somewhere.org', 'uuid'),
            ('http://overthejungle.org', 'diuu'),
    ):
        deposit = Deposit(
            client=DepositClient(provider_url=provider_url),
            external_id=external_id
        )

        actual_origin_url = utils.origin_url_from(deposit)

        assert actual_origin_url == '%s/%s' % (
            provider_url.rstrip('/'), external_id)


def test_origin_url_from_ko():
    """Badly configured deposit should raise

    """
    for provider_url, external_id in (
            (None, 'uuid'),
            ('http://overthejungle.org', None),
    ):
        deposit = Deposit(
            client=DepositClient(provider_url=provider_url),
            external_id=None
        )

        with pytest.raises(AssertionError):
            utils.origin_url_from(deposit)


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


@patch('swh.deposit.utils.normalize_timestamp', side_effect=lambda x: x)
def test_normalize_date_0(mock_normalize):
    """When date is a list, choose the first date and normalize it

    Note: We do not test swh.model.identifiers which is already tested
    in swh.model

    """
    actual_date = utils.normalize_date(['2017-10-12', 'date1'])

    expected_date = '2017-10-12 00:00:00+00:00'

    assert str(actual_date) == expected_date


@patch('swh.deposit.utils.normalize_timestamp', side_effect=lambda x: x)
def test_normalize_date_1(mock_normalize):
    """Providing a date in a reasonable format, everything is fine

    Note: We do not test swh.model.identifiers which is already tested
    in swh.model

    """
    actual_date = utils.normalize_date('2018-06-11 17:02:02')

    expected_date = '2018-06-11 17:02:02+00:00'

    assert str(actual_date) == expected_date


@patch('swh.deposit.utils.normalize_timestamp', side_effect=lambda x: x)
def test_normalize_date_doing_irrelevant_stuff(mock_normalize):
    """Providing a date with only the year results in a reasonable date

    Note: We do not test swh.model.identifiers which is already tested
    in swh.model

    """
    actual_date = utils.normalize_date('2017')

    expected_date = '2017-01-01 00:00:00+00:00'

    assert str(actual_date) == expected_date
