.. _authentication:

Authentication
==============

This is a description of the authentication mechanism used in the deposit server. Both
`basic authentication <https://tools.ietf.org/html/rfc7617>`_ and `keycloak`_ schemes
are supported through configuration.

Basic
-----

The first implementation uses `basic authentication
<https://tools.ietf.org/html/rfc7617>`_. The deposit server checks
the authentication credentials sent by the deposit client using its own database. If
authorized, the deposit client is allowed to continue its deposit. Otherwise, a 401
response is returned to the client.

.. figure:: ../images/deposit-authentication-basic.svg
   :alt: Basic Authentication


Keycloak
--------

Recent changes introduced `keycloak`_, an Open Source Identity and Access Management
tool which is already used in other parts of the swh stack.

The authentication is delegated to the `swh keycloak instance
<https://auth.softwareheritage.org/auth/>`_ using the `Resource Owner Password
Credentials <https://tools.ietf.org/html/rfc6749#section-1.3.3>`_ scheme.

Deposit clients still uses the deposit as before. Transparently for them, the deposit
server forwards their credentials to keycloak for validation. If `keycloak`_ authorizes
the deposit client, the deposit further checks that the deposit client has the proper
permission "swh.deposit.api". If they do, they can post their deposits.

If any issue arises during one of the authentication check, the client receives a 401
response (unauthorized).

.. figure:: ../images/deposit-authentication-keycloak.svg
   :alt: Keycloak Authentication

.. _keycloak: https://www.keycloak.org/
