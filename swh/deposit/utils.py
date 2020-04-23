# Copyright (C) 2018-2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import iso8601

from types import GeneratorType

from swh.model.identifiers import normalize_timestamp


def merge(*dicts):
    """Given an iterator of dicts, merge them losing no information.

    Args:
        *dicts: arguments are all supposed to be dict to merge into one

    Returns:
        dict merged without losing information

    """

    def _extend(existing_val, value):
        """Given an existing value and a value (as potential lists), merge
           them together without repetition.

        """
        if isinstance(value, (list, map, GeneratorType)):
            vals = value
        else:
            vals = [value]
        for v in vals:
            if v in existing_val:
                continue
            existing_val.append(v)
        return existing_val

    d = {}
    for data in dicts:
        if not isinstance(data, dict):
            raise ValueError("dicts is supposed to be a variable arguments of dict")

        for key, value in data.items():
            existing_val = d.get(key)
            if not existing_val:
                d[key] = value
                continue
            if isinstance(existing_val, (list, map, GeneratorType)):
                new_val = _extend(existing_val, value)
            elif isinstance(existing_val, dict):
                if isinstance(value, dict):
                    new_val = merge(existing_val, value)
                else:
                    new_val = _extend([existing_val], value)
            else:
                new_val = _extend([existing_val], value)
            d[key] = new_val
    return d


def normalize_date(date):
    """Normalize date fields as expected by swh workers.

    If date is a list, elect arbitrarily the first element of that
    list

    If date is (then) a string, parse it through
    dateutil.parser.parse to extract a datetime.

    Then normalize it through
    swh.model.identifiers.normalize_timestamp.

    Returns
        The swh date object

    """
    if isinstance(date, list):
        date = date[0]
    if isinstance(date, str):
        date = iso8601.parse_date(date)

    return normalize_timestamp(date)
