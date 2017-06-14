# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.core.urlresolvers import reverse
from io import BytesIO
from rest_framework import status
from rest_framework.test import APITestCase

from swh.deposit.config import COL_IRI, DEPOSIT_STATUS_DEPOSITED
from swh.deposit.models import Deposit, DepositRequest
from swh.deposit.parsers import parse_xml

from ..common import BasicTestCase, WithAuthTestCase


class DepositAtomEntryTestCase(APITestCase, WithAuthTestCase, BasicTestCase):
    """Try and post atom entry deposit.

    """
    def setUp(self):
        super().setUp()

        self.atom_entry_data0 = b"""<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom">
    <title>Awesome Compiler</title>
    <client>hal</client>
    <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
    <external_identifier>%s</external_identifier>
    <updated>2017-10-07T15:17:08Z</updated>
    <author>some awesome author</author>
    <applicationCategory>something</applicationCategory>
    <name>awesome-compiler</name>
    <description>This is an awesome compiler destined to
awesomely compile stuff
and other stuff</description>
    <keywords>compiler,programming,language</keywords>
    <dateCreated>2005-10-07T17:17:08Z</dateCreated>
    <datePublished>2005-10-07T17:17:08Z</datePublished>
    <releaseNotes>release note</releaseNotes>
    <relatedLink>related link</relatedLink>
    <sponsor></sponsor>
    <programmingLanguage>Awesome</programmingLanguage>
    <codeRepository>https://hoster.org/awesome-compiler</codeRepository>
    <operatingSystem>GNU/Linux</operatingSystem>
    <version>0.0.1</version>
    <developmentStatus>running</developmentStatus>
    <runtimePlatform>all</runtimePlatform>
</entry>"""

        self.atom_entry_data1 = b"""<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom">
    <client>hal</client>
    <id>urn:uuid:2225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
    <updated>2017-10-07T15:17:08Z</updated>
    <author>some awesome author</author>
    <applicationCategory>something</applicationCategory>
    <name>awesome-compiler</name>
    <description>This is an awesome compiler destined to
awesomely compile stuff
and other stuff</description>
    <keywords>compiler,programming,language</keywords>
    <dateCreated>2005-10-07T17:17:08Z</dateCreated>
    <datePublished>2005-10-07T17:17:08Z</datePublished>
    <releaseNotes>release note</releaseNotes>
    <relatedLink>related link</relatedLink>
    <sponsor></sponsor>
    <programmingLanguage>Awesome</programmingLanguage>
    <codeRepository>https://hoster.org/awesome-compiler</codeRepository>
    <operatingSystem>GNU/Linux</operatingSystem>
    <version>0.0.1</version>
    <developmentStatus>running</developmentStatus>
    <runtimePlatform>all</runtimePlatform>
</entry>"""

        self.atom_entry_data2 = b"""<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom">
    <external_identifier>%s</external_identifier>
</entry>"""

        self.atom_entry_data_empty_body = b"""<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom"></entry>"""

        self.atom_entry_data3 = b"""<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom">
    <something>something</something>
</entry>"""

        self.atom_entry_data_atom_only = b"""<?xml version="1.0"?>
            <entry xmlns="http://www.w3.org/2005/Atom">
                <title>Awesome Compiler</title>
                <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
                <external_identifier>1785io25c695</external_identifier>
                <updated>2017-10-07T15:17:08Z</updated>
                <author>some awesome author</author>
        </entry>"""

        self.atom_entry_data_codemeta = b"""<?xml version="1.0"?>
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
            </entry>"""  # noqa

        self.atom_entry_data_dc_codemeta = b"""<?xml version="1.0"?>
        <entry xmlns="http://www.w3.org/2005/Atom"
               xmlns:dcterms="http://purl.org/dc/terms/"
               xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0">


            <external_identifier>%s</external_identifier>
            <dcterms:identifier>hal-01587361</dcterms:identifier>
            <dcterms:identifier>https://hal.inria.fr/hal-01587361</dcterms:identifier>
            <dcterms:identifier>https://hal.inria.fr/hal-01587361/document</dcterms:identifier>
            <dcterms:identifier>https://hal.inria.fr/hal-01587361/file/AffectationRO-v1.0.0.zip</dcterms:identifier>
            <dcterms:identifier>doi:10.5281/zenodo.438684</dcterms:identifier>
            <dcterms:title xml:lang="en">The assignment problem</dcterms:title>
            <dcterms:title xml:lang="fr">AffectationRO</dcterms:title>
            <dcterms:creator>Gruenpeter, Morane</dcterms:creator>
            <dcterms:subject>[INFO] Computer Science [cs]</dcterms:subject>
            <dcterms:subject>[INFO.INFO-RO] Computer Science [cs]/Operations Research [cs.RO]</dcterms:subject>
            <dcterms:type>SOFTWARE</dcterms:type>
            <dcterms:abstract xml:lang="en">Project in OR: The assignment problemA java implementation for the assignment problem first release</dcterms:abstract>
            <dcterms:abstract xml:lang="fr">description fr</dcterms:abstract>
            <dcterms:created>2015-06-01</dcterms:created>
            <dcterms:available>2017-10-19</dcterms:available>
            <dcterms:language>en</dcterms:language>


            <codemeta:url>url stable</codemeta:url>
            <codemeta:version>Version sur hal </codemeta:version>
            <codemeta:softwareVersion>Version entre par lutilisateur</codemeta:softwareVersion>
            <codemeta:keywords>Mots-cls</codemeta:keywords>
            <codemeta:releaseNotes>Commentaire</codemeta:releaseNotes>
            <codemeta:referencePublication>Rfrence interne </codemeta:referencePublication>
            <codemeta:isPartOf>
                <codemeta:type> Collaboration/Projet </codemeta:type>
                <codemeta:name> nom du projet</codemeta:name>
                <codemeta:identifier> id </codemeta:identifier>
            </codemeta:isPartOf>
            <codemeta:relatedLink>Voir aussi  </codemeta:relatedLink>
            <codemeta:funding>Financement  </codemeta:funding>
            <codemeta:funding>Projet ANR </codemeta:funding>
            <codemeta:funding>Projet Europen </codemeta:funding>
            <codemeta:operatingSystem>Platform/OS </codemeta:operatingSystem>
            <codemeta:softwareRequirements>Dpendances </codemeta:softwareRequirements>
            <codemeta:developmentStatus>Etat du dveloppement </codemeta:developmentStatus>
            <codemeta:license>
                <codemeta:name>license</codemeta:name>
                <codemeta:url>url spdx</codemeta:url>
            </codemeta:license>
            <codemeta:runtimePlatform>Outils de dveloppement- outil no1 </codemeta:runtimePlatform>
            <codemeta:runtimePlatform>Outils de dveloppement- outil no2 </codemeta:runtimePlatform>
            <codemeta:codeRepository>http://code.com</codemeta:codeRepository>
            <codemeta:programmingLanguage>language 1</codemeta:programmingLanguage>
            <codemeta:programmingLanguage>language 2</codemeta:programmingLanguage>
        </entry>"""  # noqa

        self.atom_entry_tei = b"""<TEI><teiHeader><fileDesc><titleStmt><title>HAL TEI export of hal-01587083</title></titleStmt><publicationStmt><distributor>CCSD</distributor><availability status="restricted"><licence target="http://creativecommons.org/licenses/by/4.0/">Distributed under a Creative Commons Attribution 4.0 International License</licence></availability><date when="2017-10-03T17:21:03+02:00"/></publicationStmt><sourceDesc><p part="N">HAL API platform</p></sourceDesc></fileDesc></teiHeader><text><body><listBibl><biblFull><titleStmt><title xml:lang="en">questionnaire software metadata</title><author role="aut"><persName><forename type="first">Morane</forename><surname>Gruenpeter</surname></persName><email type="md5">7de56c632362954fa84172cad80afe4e</email><email type="domain">inria.fr</email><ptr type="url" target="moranegg.github.io"/><idno type="halauthorid">1556733</idno><affiliation ref="#struct-474639"/></author><editor role="depositor"><persName><forename>Morane</forename><surname>Gruenpeter</surname></persName><email type="md5">f85a43a5fb4a2e0778a77e017f28c8fd</email><email type="domain">gmail.com</email></editor></titleStmt><editionStmt><edition n="v1" type="current"><date type="whenSubmitted">2017-09-29 11:21:32</date><date type="whenModified">2017-10-03 17:20:13</date><date type="whenReleased">2017-10-03 17:20:13</date><date type="whenProduced">2017-09-29</date><date type="whenEndEmbargoed">2017-09-29</date><ref type="file" target="https://hal.inria.fr/hal-01587083/document"><date notBefore="2017-09-29"/></ref><ref type="file" subtype="author" n="1" target="https://hal.inria.fr/hal-01587083/file/questionnaire.zip"><date notBefore="2017-09-29"/></ref></edition><respStmt><resp>contributor</resp><name key="442239"><persName><forename>Morane</forename><surname>Gruenpeter</surname></persName><email type="md5">f85a43a5fb4a2e0778a77e017f28c8fd</email><email type="domain">gmail.com</email></name></respStmt></editionStmt><publicationStmt><distributor>CCSD</distributor><idno type="halId">hal-01587083</idno><idno type="halUri">https://hal.inria.fr/hal-01587083</idno><idno type="halBibtex">gruenpeter:hal-01587083</idno><idno type="halRefHtml">2017</idno><idno type="halRef">2017</idno></publicationStmt><seriesStmt/><notesStmt/><sourceDesc><biblStruct><analytic><title xml:lang="en">questionnaire software metadata</title><author role="aut"><persName><forename type="first">Morane</forename><surname>Gruenpeter</surname></persName><email type="md5">7de56c632362954fa84172cad80afe4e</email><email type="domain">inria.fr</email><ptr type="url" target="moranegg.github.io"/><idno type="halauthorid">1556733</idno><affiliation ref="#struct-474639"/></author></analytic><monogr><imprint/></monogr></biblStruct></sourceDesc><profileDesc><langUsage><language ident="en">English</language></langUsage><textClass><classCode scheme="halDomain" n="info">Computer Science [cs]</classCode><classCode scheme="halTypology" n="SOFTWARE">Software</classCode></textClass></profileDesc></biblFull></listBibl></body><back><listOrg type="structures"><org type="laboratory" xml:id="struct-474639" status="VALID"><orgName>IRILL</orgName><orgName type="acronym">Initiative pour la Recherche et l'Innovation sur le Logiciel Libre</orgName><desc><address><country key="FR"/></address><ref type="url">https://www.irill.org/</ref></desc><listRelation><relation active="#struct-93591" type="direct"/><relation active="#struct-300009" type="direct"/><relation active="#struct-300301" type="direct"/></listRelation></org><org type="institution" xml:id="struct-93591" status="VALID"><orgName>Universite Pierre et Marie Curie - Paris 6</orgName><orgName type="acronym">UPMC</orgName><desc><address><addrLine>4 place Jussieu - 75005 Paris</addrLine><country key="FR"/></address><ref type="url">http://www.upmc.fr/</ref></desc></org><org type="institution" xml:id="struct-300009" status="VALID"><orgName>Institut National de Recherche en Informatique et en Automatique</orgName><orgName type="acronym">Inria</orgName><desc><address><addrLine>Domaine de VoluceauRocquencourt - BP 10578153 Le Chesnay Cedex</addrLine><country key="FR"/></address><ref type="url">http://www.inria.fr/en/</ref></desc></org><org type="institution" xml:id="struct-300301" status="VALID"><orgName>Universite Paris Diderot - Paris 7</orgName><orgName type="acronym">UPD7</orgName><desc><address><addrLine>5 rue Thomas-Mann - 75205 Paris cedex 13</addrLine><country key="FR"/></address><ref type="url">http://www.univ-paris-diderot.fr</ref></desc></org></listOrg></back></text></TEI>"""  # noqa

        self.atom_entry_data_badly_formatted = b"""<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom"</entry>"""

        self.atom_error_with_decimal = b"""<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom" xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0">
  <title>Composing a Web of Audio Applications</title>
  <client>hal</client>
  <id>hal-01243065</id>
  <external_identifier>hal-01243065</external_identifier>
  <codemeta:url>https://hal-test.archives-ouvertes.fr/hal-01243065</codemeta:url>
  <codemeta:applicationCategory>test</codemeta:applicationCategory>
  <codemeta:name/>
  <description/>
  <codemeta:keywords>DSP programming,Web,Composability,Faust</codemeta:keywords>
  <codemeta:dateCreated>2017-05-03T16:08:47+02:00</codemeta:dateCreated>
  <codemeta:description>The Web offers a great opportunity to share, deploy and use programs without installation difficulties. In this article we explore the idea of freely combining/composing real-time audio applications deployed on the Web using Faust audio DSP language.</codemeta:description>
  <codemeta:version>1</codemeta:version>
  <codemeta:softwareVersion>10.4</codemeta:softwareVersion>
  <codemeta:runtimePlatform>phpstorm</codemeta:runtimePlatform>
  <codemeta:developmentStatus>stable</codemeta:developmentStatus>
  <codeRepository/>
  <platform>linux</platform>
  <codemeta:programmingLanguage>php</codemeta:programmingLanguage>
  <codemeta:programmingLanguage>python</codemeta:programmingLanguage>
  <codemeta:programmingLanguage>C</codemeta:programmingLanguage>
  <codemeta:license>
    <codemeta:name>GNU General Public License v3.0 only</codemeta:name>
  </codemeta:license>
  <codemeta:license>
    <codemeta:name>CeCILL Free Software License Agreement v1.1</codemeta:name>
  </codemeta:license>
  <author>
    <name>HAL</name>
    <email>hal@ccsd.cnrs.fr</email>
  </author>
  <contributor>
    <name>Someone Nice</name>
    <email>someone@nice.fr</email>
    <codemeta:affiliation>FFJ</codemeta:affiliation>
  </contributor>
</entry>
"""  # noqa

    def test_post_deposit_atom_entry_serialization_error(self):
        """Posting an initial atom entry should return 201 with deposit receipt

        """
        # given
        # when
        response = self.client.post(
            reverse(COL_IRI, args=[self.collection.name]),
            content_type='application/atom+xml;type=entry',
            data=self.atom_error_with_decimal,
            HTTP_SLUG='external-id',
            HTTP_IN_PROGRESS='false')

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_content = parse_xml(BytesIO(response.content))
        deposit_id = response_content['deposit_id']

        deposit = Deposit.objects.get(pk=deposit_id)
        dr = DepositRequest.objects.get(deposit=deposit)

        self.assertIsNotNone(dr.metadata)
        sw_version = dr.metadata.get('codemeta:softwareVersion')
        self.assertEqual(sw_version, '10.4')

    def test_post_deposit_atom_empty_body_request(self):
        """Posting empty body request should return a 400 response

        """
        response = self.client.post(
            reverse(COL_IRI, args=[self.collection.name]),
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data_empty_body)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_deposit_atom_badly_formatted_is_a_bad_request(self):
        """Posting a badly formatted atom should return a 400 response

        """
        response = self.client.post(
            reverse(COL_IRI, args=[self.collection.name]),
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data_badly_formatted)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_deposit_atom_without_slug_header_is_bad_request(self):
        """Posting an atom entry without a slug header should return a 400

        """
        url = reverse(COL_IRI, args=[self.collection.name])

        # when
        response = self.client.post(
            url,
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data0,
            # + headers
            HTTP_IN_PROGRESS='false')

        self.assertIn(b'Missing SLUG header', response.content)
        self.assertEqual(response.status_code,
                         status.HTTP_400_BAD_REQUEST)

    def test_post_deposit_atom_unknown_collection(self):
        """Posting an atom entry to an unknown collection should return a 404

        """
        response = self.client.post(
            reverse(COL_IRI, args=['unknown-one']),
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data3,
            HTTP_SLUG='something')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_deposit_atom_entry_initial(self):
        """Posting an initial atom entry should return 201 with deposit receipt

        """
        # given
        external_id = 'urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a'

        with self.assertRaises(Deposit.DoesNotExist):
            Deposit.objects.get(external_id=external_id)

        atom_entry_data = self.atom_entry_data0 % external_id.encode('utf-8')

        # when
        response = self.client.post(
            reverse(COL_IRI, args=[self.collection.name]),
            content_type='application/atom+xml;type=entry',
            data=atom_entry_data,
            HTTP_SLUG='external-id',
            HTTP_IN_PROGRESS='false')

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_content = parse_xml(BytesIO(response.content))
        deposit_id = response_content['deposit_id']

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.collection, self.collection)
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.status, DEPOSIT_STATUS_DEPOSITED)
        self.assertEqual(deposit.client, self.user)

        # one associated request to a deposit
        deposit_request = DepositRequest.objects.get(deposit=deposit)
        self.assertIsNotNone(deposit_request.metadata)
        self.assertEqual(
            deposit_request.raw_metadata, atom_entry_data.decode('utf-8'))
        self.assertFalse(bool(deposit_request.archive))

    def test_post_deposit_atom_entry_with_codemeta(self):
        """Posting an initial atom entry should return 201 with deposit receipt

        """
        # given
        external_id = 'urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a'

        with self.assertRaises(Deposit.DoesNotExist):
            Deposit.objects.get(external_id=external_id)

        atom_entry_data = self.atom_entry_data_dc_codemeta % (
            external_id.encode('utf-8'), )

        # when
        response = self.client.post(
            reverse(COL_IRI, args=[self.collection.name]),
            content_type='application/atom+xml;type=entry',
            data=atom_entry_data,
            HTTP_SLUG='external-id',
            HTTP_IN_PROGRESS='false')

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_content = parse_xml(BytesIO(response.content))

        deposit_id = response_content['deposit_id']

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.collection, self.collection)
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.status, DEPOSIT_STATUS_DEPOSITED)
        self.assertEqual(deposit.client, self.user)

        # one associated request to a deposit
        deposit_request = DepositRequest.objects.get(deposit=deposit)
        self.assertIsNotNone(deposit_request.metadata)
        self.assertEqual(
            deposit_request.raw_metadata, atom_entry_data.decode('utf-8'))

        self.assertFalse(bool(deposit_request.archive))

    def test_post_deposit_atom_entry_tei(self):
        """Posting initial atom entry as TEI should return 201 with receipt

        """
        # given
        external_id = 'urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a'
        with self.assertRaises(Deposit.DoesNotExist):
            Deposit.objects.get(external_id=external_id)

        atom_entry_data = self.atom_entry_tei

        # when
        response = self.client.post(
            reverse(COL_IRI, args=[self.collection.name]),
            content_type='application/atom+xml;type=entry',
            data=atom_entry_data,
            HTTP_SLUG=external_id,
            HTTP_IN_PROGRESS='false')

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_content = parse_xml(BytesIO(response.content))
        deposit_id = response_content['deposit_id']

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.collection, self.collection)
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.status, DEPOSIT_STATUS_DEPOSITED)
        self.assertEqual(deposit.client, self.user)

        # one associated request to a deposit
        deposit_request = DepositRequest.objects.get(deposit=deposit)
        self.assertIsNotNone(deposit_request.metadata)
        self.assertEqual(
            deposit_request.raw_metadata, atom_entry_data.decode('utf-8'))
        self.assertFalse(bool(deposit_request.archive))

    def test_post_deposit_atom_entry_multiple_steps(self):
        """After initial deposit, updating a deposit should return a 201

        """
        # given
        external_id = 'urn:uuid:2225c695-cfb8-4ebb-aaaa-80da344efa6a'

        with self.assertRaises(Deposit.DoesNotExist):
            deposit = Deposit.objects.get(external_id=external_id)

        # when
        response = self.client.post(
            reverse(COL_IRI, args=[self.collection.name]),
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data1,
            HTTP_IN_PROGRESS='True',
            HTTP_SLUG=external_id)

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_content = parse_xml(BytesIO(response.content))
        deposit_id = int(response_content['deposit_id'])

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.collection, self.collection)
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.status, 'partial')
        self.assertEqual(deposit.client, self.user)

        # one associated request to a deposit
        deposit_requests = DepositRequest.objects.filter(deposit=deposit)
        self.assertEqual(len(deposit_requests), 1)

        atom_entry_data = self.atom_entry_data2 % external_id.encode('utf-8')

        update_uri = response._headers['location'][1]

        # when updating the first deposit post
        response = self.client.post(
            update_uri,
            content_type='application/atom+xml;type=entry',
            data=atom_entry_data,
            HTTP_IN_PROGRESS='False')

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_content = parse_xml(BytesIO(response.content))
        deposit_id = int(response_content['deposit_id'])

        deposit = Deposit.objects.get(pk=deposit_id)
        self.assertEqual(deposit.collection, self.collection)
        self.assertEqual(deposit.external_id, external_id)
        self.assertEqual(deposit.status, DEPOSIT_STATUS_DEPOSITED)
        self.assertEqual(deposit.client, self.user)

        self.assertEqual(len(Deposit.objects.all()), 1)

        # now 2 associated requests to a same deposit
        deposit_requests = DepositRequest.objects.filter(
            deposit=deposit).order_by('id')
        self.assertEqual(len(deposit_requests), 2)

        expected_meta = [
            {
                'metadata': parse_xml(self.atom_entry_data1),
                'raw_metadata': self.atom_entry_data1.decode('utf-8'),
            },
            {
                'metadata': parse_xml(atom_entry_data),
                'raw_metadata': atom_entry_data.decode('utf-8'),
            }
        ]

        for i, deposit_request in enumerate(deposit_requests):
            actual_metadata = deposit_request.metadata
            self.assertEqual(actual_metadata,
                             expected_meta[i]['metadata'])
            self.assertEqual(deposit_request.raw_metadata,
                             expected_meta[i]['raw_metadata'])
            self.assertFalse(bool(deposit_request.archive))
