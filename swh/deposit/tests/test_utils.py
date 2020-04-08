# Copyright (C) 2018-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from unittest.mock import patch

from swh.deposit import utils


def test_merge():
    """Calling utils.merge on dicts should merge without losing information

    """
    d0 = {"author": "someone", "license": [["gpl2"]], "a": 1}

    d1 = {
        "author": ["author0", {"name": "author1"}],
        "license": [["gpl3"]],
        "b": {"1": "2"},
    }

    d2 = {"author": map(lambda x: x, ["else"]), "license": "mit", "b": {"2": "3",}}

    d3 = {
        "author": (v for v in ["no one"]),
    }

    actual_merge = utils.merge(d0, d1, d2, d3)

    expected_merge = {
        "a": 1,
        "license": [["gpl2"], ["gpl3"], "mit"],
        "author": ["someone", "author0", {"name": "author1"}, "else", "no one"],
        "b": {"1": "2", "2": "3",},
    }
    assert actual_merge == expected_merge


def test_merge_2():
    d0 = {"license": "gpl2", "runtime": {"os": "unix derivative"}}

    d1 = {"license": "gpl3", "runtime": "GNU/Linux"}

    expected = {
        "license": ["gpl2", "gpl3"],
        "runtime": [{"os": "unix derivative"}, "GNU/Linux"],
    }

    actual = utils.merge(d0, d1)
    assert actual == expected


def test_merge_edge_cases():
    input_dict = {
        "license": ["gpl2", "gpl3"],
        "runtime": [{"os": "unix derivative"}, "GNU/Linux"],
    }
    # against empty dict
    actual = utils.merge(input_dict, {})
    assert actual == input_dict

    # against oneself
    actual = utils.merge(input_dict, input_dict, input_dict)
    assert actual == input_dict


def test_merge_one_dict():
    """Merge one dict should result in the same dict value

    """
    input_and_expected = {"anything": "really"}
    actual = utils.merge(input_and_expected)
    assert actual == input_and_expected


def test_merge_raise():
    """Calling utils.merge with any no dict argument should raise

    """
    d0 = {"author": "someone", "a": 1}

    d1 = ["not a dict"]

    with pytest.raises(ValueError):
        utils.merge(d0, d1)

    with pytest.raises(ValueError):
        utils.merge(d1, d0)

    with pytest.raises(ValueError):
        utils.merge(d1)

    assert utils.merge(d0) == d0


@patch("swh.deposit.utils.normalize_timestamp", side_effect=lambda x: x)
def test_normalize_date_0(mock_normalize):
    """When date is a list, choose the first date and normalize it

    Note: We do not test swh.model.identifiers which is already tested
    in swh.model

    """
    actual_date = utils.normalize_date(["2017-10-12", "date1"])

    expected_date = "2017-10-12 00:00:00+00:00"

    assert str(actual_date) == expected_date


@patch("swh.deposit.utils.normalize_timestamp", side_effect=lambda x: x)
def test_normalize_date_1(mock_normalize):
    """Providing a date in a reasonable format, everything is fine

    Note: We do not test swh.model.identifiers which is already tested
    in swh.model

    """
    actual_date = utils.normalize_date("2018-06-11 17:02:02")

    expected_date = "2018-06-11 17:02:02+00:00"

    assert str(actual_date) == expected_date


@patch("swh.deposit.utils.normalize_timestamp", side_effect=lambda x: x)
def test_normalize_date_doing_irrelevant_stuff(mock_normalize):
    """Providing a date with only the year results in a reasonable date

    Note: We do not test swh.model.identifiers which is already tested
    in swh.model

    """
    actual_date = utils.normalize_date("2017")

    expected_date = "2017-01-01 00:00:00+00:00"

    assert str(actual_date) == expected_date
