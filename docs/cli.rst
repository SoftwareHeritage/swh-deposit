.. _swh-deposit-cli:

Command-line interface
======================

Shared command-line interface
-----------------------------

.. click:: swh.deposit.cli:deposit
  :prog: swh deposit
  :nested: short

Administration utilities
------------------------

.. click:: swh.deposit.cli.admin:admin
  :prog: swh deposit admin
  :nested: full

.. _swh-deposit-cli-client:

Deposit client tools
--------------------

.. click:: swh.deposit.cli.client:upload
  :prog: swh deposit
  :nested: full

.. click:: swh.deposit.cli.client:status
  :prog: swh deposit
  :nested: full

.. click:: swh.deposit.cli.client:metadata_only
  :prog: swh deposit
  :nested: full
