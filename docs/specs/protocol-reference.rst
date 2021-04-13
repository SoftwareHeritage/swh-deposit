.. _deposit-protocol:

Protocol reference
==================

The swh-deposit protocol is an extension SWORDv2_ protocol, and the
swh-deposit client and server should work with any other SWORDv2-compliant
implementation which provides some :ref:`mandatory attributes <mandatory-attributes>`

However, we define some extensions by the means of extra tags in the Atom
entries, that should be used when interacting with the server to use it optimally.
This means the swh-deposit server should work with a generic SWORDv2 client, but
works much better with these extensions.

All these tags are in the ``https://www.softwareheritage.org/schema/2018/deposit``
XML namespace, denoted using the ``swhdeposit`` prefix in this section.


Origin creation with the ``<swhdeposit:create_origin>`` tag
-----------------------------------------------------------

Motivation
^^^^^^^^^^

This is the main extension we define.
This tag is used after a deposit is completed, to load it in the Software Heritage
archive.

The SWH archive references source code repositories by an URI, called the
:term:`origin` URL.
This URI is clearly defined when SWH pulls source code from such a repository;
but not for the push approach used by SWORD, as SWORD clients do not intrinsically
have an URL.

Usage
^^^^^

Instead, clients are expected to provide the origin URL themselves, by adding
a tag in the Atom entry they submit to the server, like this:

.. code:: xml

   <atom:entry xmlns:atom="http://www.w3.org/2005/Atom"
               xmlns:swh="https://www.softwareheritage.org/schema/2018/deposit">

     <!-- ... -->

     <swh:deposit>
       <swh:create_origin>
         <swh:origin url="https://example.org/b063bf3a-e98e-40a0-b918-3e42b06011ba" />
       </swh:create_origin>
     </swh:deposit>

     <!-- ... -->

   </atom:entry>

This will create an origin in the Software Heritage archive, that will point to
the source code artifacts of this deposit.

Semantics of origin URLs
^^^^^^^^^^^^^^^^^^^^^^^^

Origin URLs must be unique to an origin, ie. to a software project.
The exact definition of a "software project" is left to the clients of the deposit.
They should be designed so that future releases of the same software will have
the same origin URL.
As a guideline, consider that every GitHub/GitLab project is an origin,
and every package in Debian/NPM/PyPI is also an origin.

While origin URLs are not required to resolve to a source code artifact,
we recommend they point to a public resource describing the software project,
including a link to download its source code.
This is not a technical requirement, but it improves discoverability.

Clients may not submit arbitrary URLs; the server will check the URLs they submit
belongs a "namespace" they own, known as the ``provider_url`` of the client.
For example, if a client has their ``provider_url`` set to ``https://example.org/foo/``
they will not be able to submit deposits to origins whose URL starts with
``https://example.org/foo/``.

Fallbacks
^^^^^^^^^

If the ``<swhdeposit:create_origin>`` is not provided (either because they are generic
SWORDv2 implementations or old implementations of an swh-deposit client), the server
falls back to creating one based on the ``provider_url`` and the ``Slug`` header
(as defined in the AtomPub_ specification) by concatenating them.
If the ``Slug`` header is missing, the server generates one randomly.

This fallback is provided for compliance with SWORDv2_ clients, but we do not
recommend relying on it, as it usually creates origins URL that are not meaningful.


Adding releases to an origin, with the ``<swhdeposit:add_to_origin>`` tag
-------------------------------------------------------------------------

When depositing a source code artifact for an origin (ie. software project) that
was already deposited before, clients should not use ``<swhdeposit:create_origin>``,
as the origin was already created by the original deposit; and
``<swhdeposit:add_to_origin>`` should be used instead.

It is used very similarly to ``<swhdeposit:create_origin>``:

.. code:: xml

   <atom:entry xmlns:atom="http://www.w3.org/2005/Atom"
               xmlns:swh="https://www.softwareheritage.org/schema/2018/deposit">

     <!-- ... -->

     <swh:deposit>
       <swh:add_to_origin>
         <swh:origin url="https://example.org/~user/repo" />
       </swh:add_to_origin>
     </swh:deposit>

     <!-- ... -->

   </atom:entry>


This will create a new :term:`revision` object in the Software Heritage archive,
with the last deposit on this origin as its parent revision,
and reference it from the origin.

If the origin does not exist, it will error.


Metadata
--------

Format
^^^^^^

While the SWORDv2 specification recommends the use of DublinCore_,
we prefer the CodeMeta_ vocabulary, as we already use it in other components
of Software Heritage.

While CodeMeta is designed for use in JSON-LD, it is easy to reuse its vocabulary
and embed it in an XML document, in three steps:

1. use the JSON-LD compact representation of the CodeMeta document
2. replace ``@context`` declarations with XML namespaces
3. unfold JSON lists to sibling XML subtrees

For example, this CodeMeta document:

.. code:: json

   {
      "@context": "https://doi.org/10.5063/SCHEMA/CODEMETA-2.0",
      "name": "My Software",
      "author": [
         {
            "name": "Author 1",
            "email": "foo@example.org"
         },
         {
            "name": "Author 2"
         }
      ]
   }

becomes this XML document:

.. code:: xml

   <?xml version="1.0"?>
   <atom:entry xmlns:atom="http://www.w3.org/2005/Atom"
               xmlns="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0">
     <name>My Software</name>
     <author>
       <name>Author 1</name>
       <email>foo@example.org</email>
     </author>
     <author>
       <name>Author 2</name>
     </author>
   </atom:entry>

Or, equivalently:

.. code:: xml

   <?xml version="1.0"?>
   <entry xmlns="http://www.w3.org/2005/Atom"
          xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0">
     <codemeta:name>My Software</codemeta:name>
     <codemeta:author>
       <codemeta:name>Author 1</codemeta:name>
       <codemeta:email>foo@example.org</codemeta:email>
     </codemeta:author>
     <codemeta:author>
       <codemeta:name>Author 2</codemeta:name>
     </codemeta:author>
   </entry>


.. _mandatory-attributes:

Mandatory attributes
^^^^^^^^^^^^^^^^^^^^

All deposits must include:

* an ``<atom:author>`` tag with an ``<atom:name>`` and ``<atom:email>``, and
* either ``<atom:name>`` or ``<atom:title>``

We also highly recommend their CodeMeta equivalent, and any other relevant
metadata, but this is not enforced.

.. _metadata-only-deposit:

Metadata-only deposit
---------------------

The swh-deposit server can also be without a source code artifact, but only
to provide metadata that describes an arbitrary origin or object in
Software Heritage; known as extrinsic metadata.

Unlike regular deposits, there are no restricting on URL prefixes,
so any client can provide metadata on any origin; and no restrictions on which
objects can be described.

This is done by simply omitting the binary file deposit request of
a regular SWORDv2 deposit, and including information on which object the metadata
describes, by adding a ``<swhdeposit:reference>`` tag in the Atom document.

To describe an origin:

.. code:: xml

   <?xml version="1.0"?>
   <entry xmlns="http://www.w3.org/2005/Atom"
          xmlns:swh="https://www.softwareheritage.org/schema/2018/deposit">

     <!-- ... -->

     <swh:deposit>
       <swh:reference>
         <swh:origin url='https://example.org/~user/repo'/>
       </swh:reference>
     </swh:deposit>

     <!-- ... -->

   </entry>

And to describe an object:

.. code:: xml

   <?xml version="1.0"?>
   <entry xmlns="http://www.w3.org/2005/Atom"
          xmlns:swh="https://www.softwareheritage.org/schema/2018/deposit">

     <!-- ... -->

     <swh:deposit>
       <swh:reference>
         <swh:object swhid="swh:1:dir:31b5c8cc985d190b5a7ef4878128ebfdc2358f49" />
       </swh:reference>
     </swh:deposit>

     <!-- ... -->

   </entry>

For details on the semantics, see the
:ref:`metadata deposit specification <spec-metadata-deposit>`


Schema
------

Here is an XML schema to summarize the syntax described in this document:

.. literalinclude:: swh.xsd
   :language: xml



.. _SWORDv2: http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html
.. _AtomPub: https://tools.ietf.org/html/rfc5023
.. _DublinCore: https://www.dublincore.org/
.. _CodeMeta: https://codemeta.github.io/
