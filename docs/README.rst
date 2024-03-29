Software Heritage - Deposit
===========================

Simple Web-Service Offering Repository Deposit (S.W.O.R.D) is an interoperability
standard for digital file deposit.

This repository is both the `SWORD v2`_ Server and a deposit command-line client
implementations.

This implementation allows interaction between a client (a repository) and a server (SWH
repository) to deposit software source code archives and associated metadata.

Description
-----------

Most of the software source code artifacts present in the SWH Archive are gathered by
the mean of :term:`loader <loader>` workers run by the SWH project from source code
origins identified by :term:`lister <lister>` workers. This is a pull mechanism: it's
the responsibility of the SWH project to gather and collect source code artifacts that
way.

Alternatively, SWH allows its partners to push source code artifacts and metadata
directly into the Archive with a push-based mechanism. By using this possibility
different actors, holding software artifacts or metadata, can preserve their assets
without having to pass through an intermediate collaborative development platform, which
is already harvested by SWH (e.g GitHub, Gitlab, etc.).

This mechanism is the ``deposit``.

The main idea is the deposit is an authenticated access to an API allowing the user to
provide source code artifacts -- with metadata -- to be ingested in the SWH Archive. The
result of that is a :ref:`SWHID <persistent-identifiers>` that can be used to uniquely
and persistently identify that very piece of source code.

This unique identifier can then be used to `reference the source code
<https://hal.archives-ouvertes.fr/hal-02446202>`_ (e.g. in a `scientific paper
<https://www.softwareheritage.org/2020/05/26/citing-software-with-style/>`_) and
retrieve it using the :ref:`vault <swh-vault>` feature of the SWH Archive platform.

The differences between a piece of code uploaded using the deposit rather than simply
asking SWH to archive a repository using the :swh_web:`save code now <save/>` feature
are:

- a deposited artifact is provided from one of the SWH partners which is regarded as a
  trusted authority,
- a deposited artifact requires metadata properties describing the source code artifact,
- a deposited artifact has a codemeta_ metadata entry attached to it,
- a deposited artifact has the same visibility on the SWH Archive than a collected
  repository,
- a deposited artifact can be searched with its provided url property on the SWH
  Archive,
- the deposit API uses the `SWORD v2`_ API, thus requires some tooling to send deposits
  to SWH. These tools are provided with this repository.

See the :ref:`deposit-user-manual` page for more details on how to use the deposit client
command line tools to push a deposit in the SWH Archive.

See the :ref:`deposit-api-specifications` reference pages of the SWORDv2 API implementation
in `swh.deposit` if you want to do upload deposits using HTTP requests.

Read the :ref:`deposit-metadata` chapter to get more details on what metadata
are supported when doing a deposit.

See :ref:`swh-deposit-dev-env` if you want to hack the code of the ``swh.deposit`` module.

See :ref:`swh-deposit-prod-env` if you want to deploy your own copy of the
`swh.deposit` stack.


.. _codemeta: https://codemeta.github.io/
.. _SWORD v2: http://swordapp.org/sword-v2/
