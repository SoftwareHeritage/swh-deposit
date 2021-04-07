.. _deposit-metadata:

Deposit metadata
================

When making a software deposit into the SWH archive, one can add
information describing the software artifact and the software project.


.. _metadata-requirements:

Metadata requirements
---------------------

- **the schema/vocabulary** used *MUST* be specified with a persistent url
  (DublinCore, DOAP, CodeMeta, etc.)

  .. code:: xml

      <entry xmlns="http://www.w3.org/2005/Atom">
      or
      <entry xmlns="http://www.w3.org/2005/Atom"
	     xmlns:dcterms="http://purl.org/dc/terms/">
      or
      <entry xmlns="http://www.w3.org/2005/Atom"
	     xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0">

- **the name** of the software deposit *MUST* be provided [atom:title,
   codemeta:name, dcterms:title]

- **the authors** of the software deposit *MUST* be provided

- **the url** representing the location of the source *MAY* be provided under
  the url tag. The url will be used for creating an origin object in the
  archive.

  .. code:: xml

      <codemeta:url>http://example.com/my_project</codemeta:url>

- **the create\_origin** tag *SHOULD* be used to specify the URL of the origin
  to create (otherwise, a fallback is created using the slug, or a random
  string if missing)

- **the description** of the software deposit *SHOULD* be provided
  [codemeta:description]: short or long description of the software

- **the license/s** of the software
  deposit *SHOULD* be provided [codemeta:license]

- other metadata *MAY* be added with terms defined by the schema in use.

Examples
--------

Using only Atom
^^^^^^^^^^^^^^^

.. code:: xml

    <?xml version="1.0"?>
        <entry xmlns="http://www.w3.org/2005/Atom"
                 xmlns:swhdeposit="https://www.softwareheritage.org/schema/2018/deposit">
            <title>Awesome Compiler</title>
            <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
            <updated>2017-10-07T15:17:08Z</updated>
            <author>some awesome author</author>
            <swhdeposit:deposit>
              <swhdeposit:create_origin>
                <swhdeposit:origin url="http://example.com/my_project" />
              </swhdeposit:create_origin>
            </swhdeposit:deposit>
    </entry>

Using Atom with CodeMeta
^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: xml

    <?xml version="1.0"?>
        <entry xmlns="http://www.w3.org/2005/Atom"
                 xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0"
                 xmlns:swhdeposit="https://www.softwareheritage.org/schema/2018/deposit">
            <title>Awesome Compiler</title>
            <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
            <swhdeposit:deposit>
              <swhdeposit:create_origin>
                <swhdeposit:origin url="http://example.com/1785io25c695" />
              </swhdeposit:create_origin>
            </swhdeposit:deposit>
            <codemeta:id>1785io25c695</codemeta:id>
            <codemeta:url>origin url</codemeta:url>
            <codemeta:identifier>other identifier, DOI, ARK</codemeta:identifier>
            <codemeta:applicationCategory>Domain</codemeta:applicationCategory>

            <codemeta:description>description</codemeta:description>
            <codemeta:keywords>key-word 1</codemeta:keywords>
            <codemeta:keywords>key-word 2</codemeta:keywords>
            <codemeta:dateCreated>creation date</codemeta:dateCreated>
            <codemeta:datePublished>publication date</codemeta:datePublished>
            <codemeta:releaseNotes>comment</codemeta:releaseNotes>
            <codemeta:referencePublication>
              <codemeta:name> article name</codemeta:name>
              <codemeta:identifier> article id </codemeta:identifier>
            </codemeta:referencePublication>
            <codemeta:isPartOf>
                <codemeta:type> Collaboration/Projet </codemeta:type>
                <codemeta:name> project name</codemeta:name>
                <codemeta:identifier> id </codemeta:identifier>
            </codemeta:isPartOf>
            <codemeta:relatedLink>see also </codemeta:relatedLink>
            <codemeta:funding>Sponsor A  </codemeta:funding>
            <codemeta:funding>Sponsor B</codemeta:funding>
            <codemeta:operatingSystem>Platform/OS </codemeta:operatingSystem>
            <codemeta:softwareRequirements>dependencies </codemeta:softwareRequirements>
            <codemeta:softwareVersion>Version</codemeta:softwareVersion>
            <codemeta:developmentStatus>active </codemeta:developmentStatus>
            <codemeta:license>
                <codemeta:name>license</codemeta:name>
                <codemeta:url>url spdx</codemeta:url>
            </codemeta:license>
            <codemeta:runtimePlatform>.Net Framework 3.0 </codemeta:runtimePlatform>
            <codemeta:runtimePlatform>Python2.3</codemeta:runtimePlatform>
            <codemeta:author>
                <codemeta:name> author1 </codemeta:name>
                <codemeta:affiliation> Inria </codemeta:affiliation>
                <codemeta:affiliation> UPMC </codemeta:affiliation>
            </codemeta:author>
            <codemeta:author>
                <codemeta:name> author2 </codemeta:name>
                <codemeta:affiliation> Inria </codemeta:affiliation>
                <codemeta:affiliation> UPMC </codemeta:affiliation>
            </codemeta:author>
            <codemeta:codeRepository>http://code.com</codemeta:codeRepository>
            <codemeta:programmingLanguage>language 1</codemeta:programmingLanguage>
            <codemeta:programmingLanguage>language 2</codemeta:programmingLanguage>
            <codemeta:issueTracker>http://issuetracker.com</codemeta:issueTracker>
        </entry>

Using Atom with DublinCore and CodeMeta (multi-schema entry)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: xml

    <?xml version="1.0"?>
    <entry xmlns="http://www.w3.org/2005/Atom"
           xmlns:dcterms="http://purl.org/dc/terms/"
           xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0"
           xmlns:swhdeposit="https://www.softwareheritage.org/schema/2018/deposit">
        <title>Awesome Compiler</title>
        <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
        <swhdeposit:deposit>
          <swhdeposit:create_origin>
            <swhdeposit:origin url="http://example.com/225c695-cfb8-4ebb-aaaa-80da344efa6a" />
          </swhdeposit:create_origin>
        <swhdeposit:deposit>
        <dcterms:identifier>hal-01587361</dcterms:identifier>
        <dcterms:identifier>doi:10.5281/zenodo.438684</dcterms:identifier>
        <dcterms:title xml:lang="en">The assignment problem</dcterms:title>
        <dcterms:title xml:lang="fr">AffectationRO</dcterms:title>
        <dcterms:creator>author</dcterms:creator>
        <dcterms:subject>[INFO] Computer Science [cs]</dcterms:subject>
        <dcterms:subject>[INFO.INFO-RO] Computer Science [cs]/Operations Research [cs.RO]</dcterms:subject>
        <dcterms:type>SOFTWARE</dcterms:type>
        <dcterms:abstract xml:lang="en">Project in OR: The assignment problemA java implementation for the assignment problem first release</dcterms:abstract>
        <dcterms:abstract xml:lang="fr">description fr</dcterms:abstract>
        <dcterms:created>2015-06-01</dcterms:created>
        <dcterms:available>2017-10-19</dcterms:available>
        <dcterms:language>en</dcterms:language>


        <codemeta:url>origin url</codemeta:url>

        <codemeta:softwareVersion>1.0.0</codemeta:softwareVersion>
        <codemeta:keywords>key word</codemeta:keywords>
        <codemeta:releaseNotes>Comment</codemeta:releaseNotes>
        <codemeta:referencePublication>Rfrence interne </codemeta:referencePublication>

        <codemeta:relatedLink>link  </codemeta:relatedLink>
        <codemeta:funding>Sponsor  </codemeta:funding>

        <codemeta:operatingSystem>Platform/OS </codemeta:operatingSystem>
        <codemeta:softwareRequirements>dependencies </codemeta:softwareRequirements>
        <codemeta:developmentStatus>Ended </codemeta:developmentStatus>
        <codemeta:license>
            <codemeta:name>license</codemeta:name>
            <codemeta:url>url spdx</codemeta:url>
        </codemeta:license>

        <codemeta:codeRepository>http://code.com</codemeta:codeRepository>
        <codemeta:programmingLanguage>language 1</codemeta:programmingLanguage>
        <codemeta:programmingLanguage>language 2</codemeta:programmingLanguage>
    </entry>

Note
----
We aim on harmonizing the metadata from different origins and thus
metadata will be translated to the `CodeMeta
v.2 <https://doi.org/10.5063/SCHEMA/CODEMETA-2.0>`__ vocabulary if
possible.
