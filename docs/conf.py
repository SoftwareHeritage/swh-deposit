import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                      "swh.deposit.settings.development")
django.setup()

# source_parsers = {
#     '.md': 'recommonmark.parser.CommonMarkParser',
# }
# source_suffix = ['.rst', '.md']

from swh.docs.sphinx.conf import *  # NoQA
