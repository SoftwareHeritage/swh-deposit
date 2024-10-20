.. _swh-deposit-register-account:

.. admonition:: Intended audience
   :class: important

   - deposit clients
   - sysadm staff members

Register account
================

.. _swh-deposit-register-account-as-deposit-client:

Becoming a deposit client is very easy, just write to deposit@softwareheritage.org
to setup the deposit partner agreement. With the agreement signed you can follow the
steps below.


As a deposit client
-------------------

For this, as a client, you need to register an account on the swh keycloak `production
<https://archive.softwareheritage.org/oidc/login/>`_
or `staging
<https://webapp.staging.swh.network/oidc/login/>`_
instance.

.. _swh-deposit-register-account-as-sysadm:

As a sysadm
-----------


1. Retrieve the deposit client login (through email exchange or any other media).

2. Require a :ref:`provider url <swh-deposit-provider-url-definition>` from the deposit
   client (through email exchange or any other media).

3. Within the keycloak `production instance <https://auth.softwareheritage.org/auth/admin/SoftwareHeritage/console/#/realms/SoftwareHeritage>`_ or `staging
   instance <https://auth.softwareheritage.org/auth/admin/SoftwareHeritageStaging/console/#/realms/SoftwareHeritageStaging>`_, add the `swh.deposit.api` role to the deposit
   client login.

4. Create an :ref:`associated deposit collection
   <swh-deposit-add-client-and-collection>` in the deposit instance.

5. Create :ref:`a deposit client <swh-deposit-add-client-and-collection>` with the
   provider url in the deposit instance.

6. To ensure everything is ok, ask the deposit client to check they can access at least
   the service document iri (authenticated).
