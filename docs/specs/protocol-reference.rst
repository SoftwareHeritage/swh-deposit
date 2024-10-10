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

.. _deposit-create_origin:

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

.. _swh-deposit-provider-url-definition:

Clients may not submit arbitrary URLs; the server will check the URLs they submit
belongs to a "namespace" they own, known as the ``provider_url`` of the client. For
example, if a client has their ``provider_url`` set to ``https://example.org/foo/`` they
will only be able to submit deposits to origins whose URL starts with
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

.. _deposit-add_to_origin:

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

1. use the `JSON-LD compact representation`_ of the CodeMeta document with
   ``@context: "https://doi.org/10.5063/SCHEMA/CODEMETA-2.0"`` and no other context;
   which implies that:

   1. Codemeta properties (whether in the ``https://codemeta.github.io/terms/``
      or ``http://schema.org/`` namespaces) are unprefixed terms
   2. other properties in the ``http://schema.org/`` namespace use `compact IRIs`_
      with the ``schema`` prefix
   3. other properties are absolute
2. replace ``@context`` declarations with a XMLNS declaration with
   ``https://doi.org/10.5063/SCHEMA/CODEMETA-2.0`` as namespace
   (eg. ``xmlns="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0"``
   or ``xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0"``)
3. if using a non-default namespace, apply its prefix to any unprefixed term
   (ie. any term defined in https://doi.org/10.5063/SCHEMA/CODEMETA-2.0 )
4. add XMLNS declarations for any other prefix (eg. ``xmlns:schema="http://schema.org/"``
   if any property in that namespace is used)
5. unfold JSON lists to sibling XML subtrees

.. _JSON-LD compact representation: https://www.w3.org/TR/json-ld11/#compacted-document-form
.. _compact IRIs: https://www.w3.org/TR/json-ld11/#compact-iris

Example Codemeta document
"""""""""""""""""""""""""

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


Note that in both these examples, ``codemeta:name`` is used even though
the property is actually ``http://schema.org/name``.

Example generic JSON-LD document
""""""""""""""""""""""""""""""""

Another example using properties not part of Codemeta:

.. code:: json

   {
      "@context": "https://doi.org/10.5063/SCHEMA/CODEMETA-2.0",
      "name": "My Software",
      "schema:sameAs": "http://example.org/my-software"
   }

which is equivalent to:

.. code:: json

   {
      "@context": "https://doi.org/10.5063/SCHEMA/CODEMETA-2.0",
      "name": "My Software",
      "http://schema.org/sameAs": "http://example.org/my-software"
   }

becomes this XML document:

.. code:: xml

   <?xml version="1.0"?>
   <atom:entry xmlns:atom="http://www.w3.org/2005/Atom"
               xmlns="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0"
               xmlns:schema="http://schema.org/">
     <name>My Software</name>
     <schema:sameAs>http://example.org/my-software</schema:sameAs>
   </atom:entry>

Or, equivalently:

.. code:: xml

   <?xml version="1.0"?>
   <entry xmlns="http://www.w3.org/2005/Atom"
          xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0"
          xmlns:schema="http://schema.org/">
     <codemeta:name>My Software</codemeta:name>
     <schema:sameAs>http://example.org/my-software</schema:sameAs>
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


.. _deposit-metadata-provenance:

Metadata provenance
-------------------

To indicate where the metadata is coming from, deposit clients can use a
``<swhdeposit:metadata-provenance>`` element in ``<swhdeposit:deposit>`` whose content is
the object the metadata is coming from,
preferably using the ``http://schema.org/`` namespace.

For example, when the metadata is coming from Wikidata, then the
``<swhdeposit:metadata-provenance>`` should be the page of a Q-entity, such as
``https://www.wikidata.org/wiki/Q16988498`` (not the Q-entity
``http://www.wikidata.org/entity/Q16988498`` itself, as the Q-entity **is** the
object described in the metadata)
Or when the metadata is coming from a curated repository like HAL, then
``<swhdeposit:metadata-provenance>`` should be the HAL project.

In particular, Software Heritage expects the ``<swhdeposit:metadata-provenance>`` object
to have a ``http://schema.org/url`` property, so that it can appropriately link
to the original page.

For example, to deposit metadata on GNU Hello:

.. code:: xml

   <?xml version="1.0"?>
   <entry xmlns="http://www.w3.org/2005/Atom"
          xmlns:schema="http://schema.org/">

     <!-- ... -->

     <swh:deposit>
       <swh:metadata-provenance>
         <schema:url>https://www.wikidata.org/wiki/Q16988498</schema:url>
       </swh:metadata-provenance>
     </swh:deposit>

     <!-- ... -->

   </entry>

Here is a more complete example of a metadata-only deposit on version 2.9 of GNU Hello,
to show the interaction with other fields,

.. code:: xml

   <?xml version="1.0"?>
   <entry xmlns="http://www.w3.org/2005/Atom"
          xmlns:swh="https://www.softwareheritage.org/schema/2018/deposit"
          xmlns:schema="http://schema.org/"
          xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0">

     <swh:deposit>
       <swh:reference>
         <swh:object swhid="swh:1:dir:9b6f93b12a500f560796c8dffa383c7f4470a12f;origin=https://ftp.gnu.org/gnu/hello/;visit=swh:1:snp:1abd6aa1901ba0aa7f5b7db059250230957f8434;anchor=swh:1:rev:3d41fbdb693ba46fdebe098782be4867038503e2" />
       </swh:reference>

       <swh:metadata-provenance>
         <schema:url>https://www.wikidata.org/wiki/Q16988498</schema:url>
       </swh:metadata-provenance>
     </swh:deposit>

     <codemeta:name>GNU Hello</codemeta:name>
     <codemeta:id>http://www.wikidata.org/entity/Q16988498</codemeta:id>
     <codemeta:url>https://www.gnu.org/software/hello/</codemeta:url>

     <!-- is part of the GNU project -->
     <codemeta:isPartOf>http://www.wikidata.org/entity/Q7598</codemeta:isPartOf>

   </entry>


Schema
------

Here is an XML schema to summarize the syntax described in this document:
https://gitlab.softwareheritage.org/swh/devel/swh-deposit/-/blob/master/swh/deposit/xsd/swh.xsd



.. _SWORDv2: http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html
.. _AtomPub: https://tools.ietf.org/html/rfc5023
.. _DublinCore: https://www.dublincore.org/
.. _CodeMeta: https://codemeta.github.io/
