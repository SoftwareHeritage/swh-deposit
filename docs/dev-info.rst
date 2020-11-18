.. _swh-deposit-dev:

Hacking on swh-deposit
======================

There are multiple modes to run and test the server locally:

* development-like (automatic reloading when code changes)
* production-like (no reloading)
* integration tests (no side effects)

Except for the tests which are mostly side effects free (except for the
database access), the other modes will need some configuration files (up to 2)
to run properly.

Database
--------

swh-deposit uses a database to store the state of a deposit. The default
db is expected to be called swh-deposit-dev.

To simplify the use, the following makefile targets can be used:

schema
~~~~~~

.. code:: shell

    make db-create db-prepare db-migrate

data
~~~~

Once the db is created, you need some data to be injected (request
types, client, collection, etc...):

.. code:: shell

    make db-load-data db-load-private-data

The private data are about having a user (``hal``) with a password
(``hal``) who can access a collection (``hal``).

Add the following to ``../private-data.yaml``:

.. code:: yaml

    - model: deposit.depositclient
      fields:
        user_ptr_id: 1
        collections:
          - 1
    - model: auth.User
      pk: 1
      fields:
        first_name: hal
        last_name: hal
        username: hal
        password: "pbkdf2_sha256$30000$8lxjoGc9PiBm$DO22vPUJCTM17zYogBgBg5zr/97lH4pw10Mqwh85yUM="
    - model: deposit.depositclient
      fields:
        user_ptr_id: 1
        collections:
          - 1
        url: https://hal.inria.fr

drop
~~~~

For information, you can drop the db:

.. code:: shell

    make db-drop

Development-like environment
----------------------------

Development-like environment needs one configuration file to work
properly.

Configuration
~~~~~~~~~~~~~

**``{/etc/softwareheritage | ~/.config/swh | ~/.swh}``/deposit/server.yml**:

.. code:: yaml

    # dev option for running the server locally
    host: 127.0.0.1
    port: 5006

    # production
    authentication:
      activated: true
      white-list:
        GET:
          - /

    # 20 Mib max size
    max_upload_size: 20971520

Run
~~~

Run the local server, using the default configuration file:

.. code:: shell

    make run-dev

Production-like environment
---------------------------

Production-like environment needs additional section in the
configuration file to work properly.

This is more close to what's actually running in production.

Configuration
~~~~~~~~~~~~~

This expects the same file describes in the previous chapter. Plus, an
additional private section file containing private information that is
not in the source code repository.

**``{/etc/softwareheritage | ~/.config/swh | ~/.swh}``/deposit/private.yml**:

.. code:: yaml

  private:
    secret_key: production-local
    db:
      name: swh-deposit-dev

A production configuration file would look like:

.. code:: yaml

  private:
    secret_key: production-secret-key
      db:
        name: swh-deposit-dev
        host: db
        port: 5467
        user: user
        password: user-password

Run
~~~

.. code:: shell

    make run

Note: This expects gunicorn3 package installed on the system

Tests
-----

To run the tests:

.. code:: shell

    make test

As explained, those tests are mostly side-effect free. The db part is
dealt with by django. The remaining part which patches those side-effect
behavior is dealt with in the ``swh/deposit/tests/__init__.py`` module.

Sum up
------

Prepare everything for your user to run:

.. code:: shell

    make db-drop db-create db-prepare db-migrate db-load-private-data run-dev
