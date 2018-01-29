Use cases
---------


Deposit creation
~~~~~~~~~~~~~~~~

From client's deposit repository server to SWH's repository server:

1. The client requests for the server's abilities and its associated collection
  (GET query to the *SD/service document uri*)

2. The server answers the client with the service document which gives the
  *collection uri* (also known as *COL/collection IRI*).

3. The client sends a deposit (optionally a zip archive, some metadata or both)
  through the *collection uri*.

  This can be done in:

  * one POST request (metadata + archive).
  * one POST request (metadata or archive) + other PUT or POST request to the
    *update uris* (*edit-media iri* or *edit iri*)

  1. Server validates the client's input or returns detailed error if any

  2. Server stores information received (metadata or software archive source
     code or both)

4. The server notifies the client it acknowledged the client's request. An
  ``http 201 Created`` response with a deposit receipt in the body response is
  sent back. That deposit receipt will hold the necessary information to
  eventually complete the deposit later on if it was incomplete (also known as
  status ``partial``).

Schema representation
^^^^^^^^^^^^^^^^^^^^^

.. raw:: html

   <!-- {F2884278} -->

.. figure:: /images/deposit-create-chart.png
   :alt:


Updating an existing deposit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

5. Client updates existing deposit through the *update uris* (one or more POST
   or PUT requests to either the *edit-media iri* or *edit iri*).

  1. Server validates the client's input or returns detailed error if any

  2. Server stores information received (metadata or software archive source
     code or both)

    This would be the case for example if the client initially posted a
    ``partial`` deposit (e.g. only metadata with no archive, or an archive
    without metadata, or a splitted archive because the initial one exceeded
    the limit size imposed by swh repository deposit)

Schema representation
^^^^^^^^^^^^^^^^^^^^^

.. raw:: html

   <!-- {F2884302} -->

.. figure:: /images/deposit-update-chart.png
   :alt:

Deleting deposit (or associated archive, or associated metadata)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

6. Deposit deletion is possible as long as the deposit is still in ``partial``
   state.

  1. Server validates the client's input or returns detailed error if any
  2. Server actually delete information according to request

Schema representation
^^^^^^^^^^^^^^^^^^^^^

.. raw:: html

   <!-- {F2884311} -->

.. figure:: /images/deposit-delete-chart.png
   :alt:

Client asks for operation status
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

7. Operation status can be read through a GET query to the *state iri*.

Server: Triggering deposit checks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once the status ``deposited`` is reached for a deposit, checks for the
associated archive(s) and metadata will be triggered. If those checks
fail, the status is changed to ``rejected`` and nothing more happens
there. Otherwise, the status is changed to ``verified``.

Server: Triggering deposit load
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once the status ``verified`` is reached for a deposit, loading the
deposit with its associated metadata will be triggered.

The loading will result on status update, either ``done`` or ``failed``
(depending on the loading's status).

This is described in the `loading document <./spec-loading.html>`__.
