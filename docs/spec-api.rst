.. _swh-api-specifications:

API Documentation
=================

This is `Software Heritage <https://www.softwareheritage.org>`__'s
`SWORD
2.0 <http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html>`__
Server implementation.

**S.W.O.R.D** (**S**\ imple **W**\ eb-Service **O**\ ffering
**R**\ epository **D**\ eposit) is an interoperability standard for
digital file deposit.

This implementation will permit interaction between a client (a repository) and
a server (SWH repository) to push deposits of software source code archives
with associated metadata.

*Note:*

* In the following document, we will use the ``archive`` or ``software source
  code archive`` interchangeably.
* The supported archive formats are:

  * zip: common zip archive (no multi-disk zip files).
  * tar: tar archive without compression or optionally any of the following
    compression algorithm gzip (.tar.gz, .tgz), bzip2 (.tar.bz2) , or lzma
    (.tar.lzma)

.. _swh-deposit-collection:

Collection
----------

SWORD defines a ``collection`` concept. In SWH's case, this collection
refers to a group of deposits. A ``deposit`` is some form of software
source code archive(s) associated with metadata.
By default the client's collection will have the client's name.

Limitations
-----------
* upload limitation of 100Mib
* no mediation

API overview
------------

API access is over HTTPS.

The API is protected through basic authentication.


Endpoints
---------

The API endpoints are rooted at https://deposit.softwareheritage.org/1/.

Data is sent and received as XML (as specified in the SWORD 2.0
specification).

.. include:: endpoints/service-document.rst

.. include:: endpoints/collection.rst

.. include:: endpoints/update-media.rst

.. include:: endpoints/update-metadata.rst

.. include:: endpoints/status.rst

.. include:: endpoints/content.rst


Possible errors:
----------------

* common errors:

  * :http:statuscode:`401`:if a client does not provide credential or provide
    wrong ones
  * :http:statuscode:`403` a client tries access to a collection it does not own
  * :http:statuscode:`404` if a client tries access to an unknown collection
  * :http:statuscode:`404` if a client tries access to an unknown deposit
  * :http:statuscode:`415` if a wrong media type is provided to the endpoint

* archive/binary deposit:

  * :http:statuscode:`403` the length of the archive exceeds the max size
    configured
  * :http:statuscode:`412` the length or hash provided mismatch the reality of
    the archive.
  * :http:statuscode:`415` if a wrong media type is provided

* multipart deposit:

  * :http:statuscode:`412` the md5 hash provided mismatch the reality of the
    archive
  * :http:statuscode:`415` if a wrong media type is provided

* Atom entry deposit:

  * :http:statuscode:`400` if the request's body is empty (for creation only)




Sources
-------

* `SWORD v2 specification
  <http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html>`__
* `arxiv documentation <https://arxiv.org/help/submit_sword>`__
* `Dataverse example <http://guides.dataverse.org/en/4.3/api/sword.html>`__
* `SWORD used on HAL <https://api.archives-ouvertes.fr/docs/sword>`__
* `xml examples for CCSD <https://github.com/CCSDForge/HAL/tree/master/Sword>`__
