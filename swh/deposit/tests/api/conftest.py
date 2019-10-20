# Copyright (C) 2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from os import path, listdir
from typing import Mapping


@pytest.fixture
def atom_dataset(datadir) -> Mapping[str, bytes]:
    """Compute the paths to atom files.

    Returns:
        Dict of atom name per content (bytes)

    """
    atom_path = path.join(datadir, 'atom')

    data = {}
    for filename in listdir(atom_path):
        filepath = path.join(atom_path, filename)
        with open(filepath, 'rb') as f:
            raw_content = f.read()

        # Keep the filename without extension
        atom_name = filename.split('.')[0]
        data[atom_name] = raw_content

    return data
