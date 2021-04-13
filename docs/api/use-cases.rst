.. _deposit-use-cases:

Use cases
=========

The general idea is that a deposit can be created either in a single request
or by multiple requests to allow the user to add elements to the deposit piece
by piece (be it the deposited data or the metadata describing it).

An update request that does not have the `In-Progress: true` HTTP header will
de facto declare the deposit as *completed* (aka in the `deposited` status; see
below) and thus ready for ingestion.

Once the deposit is declared *complete* by the user, the server performs a few
validation checks. Then, if valid, schedule the ingestion of the deposited data
in the Software Heritage Archive (SWH).

There is a `status` property attached to a deposit allowing to follow the
processing workflow of the deposit. For example, when this ingestion task
completes successfully, the deposit is marked as `done`.


Possible deposit statuses are:

partial
   The deposit is partially received, since it can be done in
   multiple requests.

expired
   Deposit was there too long and is new deemed ready to be
   garbage-collected.

deposited
   Deposit is complete, ready to be checked.

rejected
  Deposit failed the checks.

verified
   Deposit passed the checks and is ready for loading.

loading
   Injection is ongoing on SWH's side.

done
   Loading is successful.

failed
   Loading failed.

.. figure:: ../images/status.svg
   :alt:

This document describes the possible scenarios for creating or updating a
deposit.


Deposit creation
----------------

From client's deposit repository server to SWH's repository server:

1. The client requests for the server's abilities and its associated
   :ref:`collections <swh-deposit-collection>` using the *SD/service document uri*
   (:http:get:`/1/servicedocument/`).

2. The server answers the client with the service document which lists the
   *collections* linked to the user account (most of the time, there will one and
   only one collection linked to the user's account). Each of these collection can
   be used to push a deposit via its *COL/collection IRI*.

3. The client sends a deposit (a zip archive, some metadata or both) through
   the *COL/collection uri*.

   This can be done in:

   * one POST request (metadata + archive) without the `In-Progress: true` header:

     - :http:post:`/1/(str:collection-name)/`

   * one POST request (metadata or archive) **with** `In-Progress: true` header:

     - :http:post:`/1/(str:collection-name)/`

     plus one or more PUT or POST requests *to the update uris*
     (*edit-media iri* or *edit iri*):

     - :http:post:`/1/(str:collection-name)/(int:deposit-id)/media/`
     - :http:put:`/1/(str:collection-name)/(int:deposit-id)/media/`
     - :http:post:`/1/(str:collection-name)/(int:deposit-id)/metadata/`
     - :http:put:`/1/(str:collection-name)/(int:deposit-id)/metadata/`

   Then:

   a. Server validates the client's input or returns detailed error if any.

   b. Server stores information received (metadata or software archive source
      code or both).

4. The server creates a loading task and submits it to the
   :ref:`Job Scheduler <swh-scheduler>`

5. The server notifies the client it acknowledged the client's request. An
   ``http 201 Created`` response with a deposit receipt in the body response is
   sent back. That deposit receipt will hold the necessary information to
   eventually complete the deposit later on if it was incomplete (also known as
   status ``partial``).

Schema representation
^^^^^^^^^^^^^^^^^^^^^

Scenario: pushing a deposit via the SWORDv2_ protocol (nominal scenario):

.. figure:: ../images/deposit-create-chart.svg
   :alt:


Deposit update
--------------

6. Client updates existing deposit through the *update uris* (one or more POST
   or PUT requests to either the *edit-media iri* or *edit iri*).

  1. Server validates the client's input or returns detailed error if any

  2. Server stores information received (metadata or software archive source
     code or both)

This would be the case for example if the client initially posted a
``partial`` deposit (e.g. only metadata with no archive, or an archive
without metadata, or a split archive because the initial one exceeded
the limit size imposed by swh repository deposit).

The content of a deposit can only be updated while it is in the ``partial``
state; this causes the content to be **replaced** (the old version is discarded).

Its metadata, however, can also be updated while in the ``done`` state; see below.


Schema representation
^^^^^^^^^^^^^^^^^^^^^

Scenario: updating a deposit via SWORDv2_ protocol:

.. figure:: ../images/deposit-update-chart.svg
   :alt:


Deposit deletion (or associated archive, or associated metadata)
----------------------------------------------------------------

7. Deposit deletion is possible as long as the deposit is still in ``partial``
   state.

  1. Server validates the client's input or returns detailed error if any
  2. Server actually delete information according to request


Schema representation
^^^^^^^^^^^^^^^^^^^^^

Scenario: deleting a deposit via SWORDv2_ protocol:

.. figure:: ../images/deposit-delete-chart.svg
   :alt:


Client asks for operation status
--------------------------------

At any time during the next step, operation status can be read through
a GET query to the *state iri*.


Deposit loading
---------------

In one of the previous steps, when a deposit was created or loaded without
``In-Progress: true``, the deposit server created a load task and submitted it
to :ref:`swh-scheduler <swh-scheduler>`.

This triggers the following steps:


Server: Triggering deposit checks
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once the status ``deposited`` is reached for a deposit, checks for the
associated archive(s) and metadata will be triggered. If those checks
fail, the status is changed to ``rejected`` and nothing more happens
there. Otherwise, the status is changed to ``verified``.


Server: Triggering deposit load
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once the status ``verified`` is reached for a deposit, loading the
deposit with its associated metadata will be triggered.

The loading will result on status update, either ``done`` or ``failed``
(depending on the loading's status).

This is described in the :ref:`loading specifications document <swh-loading-specs>`.


Completing the deposit
----------------------

When this is all done, the loaders notify the deposit server, which sets
the deposit status to ``done``.

This can then be polled by deposit clients, using the *state iri*.


Deposit metadata updates
------------------------

We saw earlier that a deposit can only be updated when in ``partial`` state.

This is one exception to this rule: its metadata can be updated while in the
``done`` state; which adds a new version of the metadata in the SWH archive,
**in addition to** the old one(s).
In this state, ``In-Progress`` is not allowed, so the deposit cannot go back
in the ``partial`` state, but only to ``deposited``.
As a failsafe, to avoid accidentally updating the wrong deposit, this requires
the ``X-Check-SWHID`` HTTP header to be set to the value of the SWHID of the
deposit's content (returned after the deposit finished loading).

.. _use-case-metadata-only-deposit:

Metadata-only deposit
---------------------

Finally, as an extension to the SWORD protocol, swh-deposit allows a special
type of deposit: metadata-only deposits.
Unlike regular deposit (described above), they do not have a code archive.
Instead, they describe an existing :term:`software artifact` present in the
archive.

This use case is triggered by a ``<reference>`` tag in the Atom document,
see the :ref:`protocol reference <metadata-only-deposit>` for details.

In the current implementation, these deposits are loaded (or rejected)
immediately after a request without ``In-Progress: true`` is made,
ie. they skip the ``loading`` state. This may change in a future version.

.. _SWORDv2: http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html
