.. _swh-deposit-deployment:

Deployment of the swh-deposit
=============================

The debian package is created and uploaded to the swh debian repository. Once the
package is installed, some further actions may be required in regards to the database
backend.

Prepare the database setup (existence, connection, etc...).
-----------------------------------------------------------

This is defined through the packaged module ``swh.deposit.settings.production`` and the
expected **/etc/softwareheritage/deposit/server.yml** configuration file.

The expected configuration files are deployed through our puppet manifest (cf.
puppet-environment/swh-site, puppet-environment/swh-role,
puppet-environment/swh-profile)

Environment (production/staging)
--------------------------------

`SWH_CONFIG_FILENAME` must be defined and target the deposit server configuration file.
So either 1. prefix the following commands or 2. export the environment variable in your
shell session. For the remaining part of the documentation, we assume 2. has been
configured.

.. code:: shell

    export SWH_CONFIG_FILENAME=/etc/softwareheritage/deposit/server.yml

Migrate/bootstrap the db schema
-------------------------------

.. code:: shell

    sudo django-admin migrate --settings=swh.deposit.settings.production

Load minimum defaults data
--------------------------

When boostraping the db schema, some default values may be needed:

.. code:: shell

    sudo django-admin loaddata \
      --settings=swh.deposit.settings.production deposit_data

This adds the minimal 'hal' collection

Note: swh.deposit.fixtures.deposit\_data is packaged.

Add client and collection
-------------------------

The deposit can now be configured to use either the 1. django basic authentication
framework or the 2. swh keycloak instance. If the server uses 2., the password is
managed by keycloak so the option `--password`` is ignored.

.. code:: shell

    swh deposit admin \
        --config-file $SWH_CONFIG_FILENAME \
        --platform production \
        user create \
        --collection <collection-name> \
        --username <client-name> \
        --password <to-define>

This adds a user ``<client-name>`` which can access the collection
``<collection-name>``. The password will be used for checking the authentication access
to the deposit api (if 1. is used).

Note:
  - If the collection does not exist, it is created alongside
  - The password, if required, is passed as plain text but stored encrypted

Reschedule a deposit
---------------------

.. code:: shell

    swh deposit admin \
        --config-file $SWH_CONFIG_FILENAME \
        --platform production \
        deposit reschedule \
        --deposit-id <deposit-id>

This will:

- check the deposit's status to something reasonable (failed or done). That means that
  the checks have passed but something went wrong during the loading (failed: loading
  failed, done: loading ok, still for some reasons as in bugs, we need to reschedule it)
- reset the deposit's status to 'verified' (prior to any loading but after the checks
  which are fine) and removes the different archives' identifiers (swh-id, ...)
- trigger back the loading task through the scheduler

Integration checks
==================

There exists icinga checks running periodically on `staging`_ and `production`_
instances. If any problem arises, expect those to notify the #swh-sysadm irc channel.

.. _staging: https://icinga.softwareheritage.org/search?q=deposit#!/monitoring/service/show?host=pergamon.softwareheritage.org&service=staging%20Check%20deposit%20end-to-end
.. _production: https://icinga.softwareheritage.org/search?q=deposit#!/monitoring/service/show?host=pergamon.softwareheritage.org&service=production%20Check%20deposit%20end-to-end
