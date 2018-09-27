import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                      "swh.deposit.settings.development")
django.setup()

from swh.docs.sphinx.conf import *  # noqa
from swh.docs.sphinx.conf import autodoc_mock_imports

autodoc_mock_imports += [
    'swh.deposit.settings',
]
