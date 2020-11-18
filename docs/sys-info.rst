.. _swh-deposit-deployment:

Deployment of the swh-deposit
=============================

As usual, the debian packaged is created and uploaded to the swh debian
repository. Once the package is installed, we need to do a few things in
regards to the database.

Prepare the database setup (existence, connection, etc...).
-----------------------------------------------------------

This is defined through the packaged ``swh.deposit.settings.production``
module and the expected **/etc/softwareheritage/deposit/server.yml**.

As usual, the expected configuration files are deployed through our
puppet manifest (cf. puppet-environment/swh-site,
puppet-environment/swh-role, puppet-environment/swh-profile)

Environment (production)
------------------------

`SWH_CONFIG_FILENAME` must be defined and target the deposit's server
configuration file. So either prefix the following commands or export the
environment variable in your shell session.

.. code:: shell

    export SWH_CONFIG_FILENAME=/etc/softwareheritage/deposit/server.yml

Migrate/bootstrap the db schema
-------------------------------

.. code:: shell

    sudo django-admin migrate --settings=swh.deposit.settings.production

Load minimum defaults data
--------------------------

.. code:: shell

    sudo django-admin loaddata \
      --settings=swh.deposit.settings.production deposit_data

This adds the minimal 'hal' collection

Note: swh.deposit.fixtures.deposit\_data is packaged

Add client and collection
-------------------------

.. code:: shell

    swh deposit admin \
        --config-file /etc/softwareheritage/deposit/server.yml \
        --platform production \
        user create \
        --collection <collection-name> \
        --username <client-name> \
        --password <to-define>

This adds a user ``<client-name>`` which can access the collection
``<collection-name>``. The password will be used for the authentication
access to the deposit api.

Note:
  - If the collection does not exist, it is created alongside
  - The password is plain text but stored encrypted (so yes, for now
    we know the user's password)
  - For production platform, you must either set an `SWH_CONFIG_FILENAME`
    environment variable or pass alongside the `--config-file` parameter

Reschedule a deposit
---------------------

.. code:: shell

    swh deposit admin \
        --config-file /etc/softwareheritage/deposit/server.yml \
        --platform production \
        deposit reschedule \
        --deposit-id <deposit-id>

This will:

- check the deposit's status to something reasonable (failed or done). That
  means that the checks have passed alright but something went wrong during the
  loading (failed: loading failed, done: loading ok, still for some reasons as
  in bugs, we need to reschedule it)
- reset the deposit's status to 'verified' (prior to any loading but after the
  checks which are fine) and removes the different archives' identifiers
  (swh-id, ...)
- trigger back the loading task through the scheduler
