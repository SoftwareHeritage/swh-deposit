Technical specifications
========================

Requirements
~~~~~~~~~~~~

*  one dedicated database to store the deposit's state - swh-deposit
*  one dedicated temporary storage to store archives before loading
*  one client to test the communication with SWORD protocol

Deposit reception schema
~~~~~~~~~~~~~~~~~~~~~~~~

* SWORD imposes the use of basic authentication, so we need a way to
  authenticate client. Also, a client can access collections:

  **deposit\_client** table:

    - id (bigint): Client's identifier
    - username  (str): Client's username
    - password (pass): Client's encrypted password
    - collections ([id]): List of collections the client can access

* Collections group deposits together:

  **deposit\_collection** table:

    - id (bigint): Collection's identifier
    - name (str): Collection's human readable name

*  A deposit is the main object the repository is all about:

   **deposit** table:

   - id (bigint): deposit's identifier
   - reception\_date (date): First deposit's reception date
   - complete\_data (date): Date when the deposit is deemed complete and ready
     for loading
   - collection (id): The collection the deposit belongs to
   - external id (text): client's internal identifier (e.g hal's id, etc...).
   - client\_id (id) : Client which did the deposit
   - swh\_id (str) : swh identifier result once the loading is complete
   - status (enum): The deposit's current status

- As mentioned, a deposit can have a status, whose possible values are:

  .. code:: text

        'partial',   -- the deposit is new or partially received since it
                     -- can be done in multiple requests
        'expired',   -- deposit has been there too long and is now deemed
                     -- ready to be garbage collected
        'deposited'  -- deposit complete, it is ready to be checked to ensure data consistency
        'verified',  -- deposit is fully received, checked, and ready for loading
        'loading',   -- loading is ongoing on swh's side
        'done',      -- loading is successful
        'failed'     -- loading is a failure

* A deposit is stateful and can be made in multiple requests:

  **deposit\_request** table:

  - id (bigint): identifier
  - type (id): deposit request's type (possible values: 'archive', 'metadata')
  - deposit\_id (id): deposit whose request belongs to
  - metadata: metadata associated to the request
  - date (date): date of the requests

  Information sent along a request are stored in a ``deposit_request`` row.

  They can be either of type ``metadata`` (atom entry, multipart's atom entry
  part) or of type ``archive`` (binary upload, multipart's binary upload part).

  When the deposit is complete (status ``deposited``), those ``metadata`` and
  ``archive`` deposit requests will be read and aggregated. They will then be
  sent as parameters to the loading routine.

  During loading, some of those metadata are kept in the ``origin_metadata``
  table and some other are stored in the ``revision`` table (see `metadata
  loading <#metadata-loading>`__).

  The only update actions occurring on the deposit table are in regards of:

    - status changes (see figure below):

       - ``partial`` -> {``expired``/``deposited``},
       - ``deposited`` -> {``rejected``/``verified``},
       - ``verified`` -> ``loading``
       - ``loading`` -> {``done``/``failed``}

    - ``complete_date`` when the deposit is
      finalized (when the status is changed to ``deposited``)
    - ``swh-id`` is populated once we have the loading result

.. figure:: ../images/status.svg
   :alt:
