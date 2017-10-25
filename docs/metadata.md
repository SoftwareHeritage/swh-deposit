# Deposit metadata

When making a software deposit into the SWH archive, one can add information
describing the software artifact and the software project.
and the metadata will be translated to the [CodeMeta v.2](https://doi.org/10.5063/SCHEMA/CODEMETA-2.0) vocabulary
if possible.

## Metadata requirements

MUST
- the schema/vocabulary used *MUST* be specified with a persistant url
(DublinCore, DOAP, CodeMeta, etc.)
- the origin url *MUST* be defined depending on the schema you use:
```XML
<link href="hal.archives-ouvertes.fr"/>
<url>hal.archives-ouvertes.fr</url>
<codemeta:url>hal.archives-ouvertes.fr</codemeta:url>
<dcterms:url>hal.archives-ouvertes.fr</dcterms:url>
```


SHOULD
- the external_identifier *SHOULD* match the Slug external-identifier in
the header
- the following metadata *SHOULD* be included using the correct terminology
(depending on the schema you are using- the CodeMeta crosswalk table can
  help you identify the terms):
  - codemeta:name - the software artifact title
  - codemeta:description - short or long description of the software in the
  deposit
  - codemeta:license - the software license/s
  - codemeta:author - the software authors

MAY
  - other metadata *MAY* be added with terms defined by the schema in use.

## Examples
### Using only Atom
```XML
<?xml version="1.0"?>
    <entry xmlns="http://www.w3.org/2005/Atom">
        <title>Awesome Compiler</title>
        <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
        <external_identifier>1785io25c695</external_identifier>
        <updated>2017-10-07T15:17:08Z</updated>
        <author>some awesome author</author>
</entry>
```
### Using Atom with CodeMeta
```XML
<?xml version="1.0"?>
    <entry xmlns="http://www.w3.org/2005/Atom"
             xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0">
        <title>Awesome Compiler</title>
        <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
        <external_identifier>1785io25c695</external_identifier>
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
```
### Using Atom with DublinCore and CodeMeta (multi-schema entry)
``` XML
<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom"
       xmlns:dcterms="http://purl.org/dc/terms/"
       xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0">
    <title>Awesome Compiler</title>
    <client>hal</client>
    <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
    <external_identifier>%s</external_identifier>
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
```
