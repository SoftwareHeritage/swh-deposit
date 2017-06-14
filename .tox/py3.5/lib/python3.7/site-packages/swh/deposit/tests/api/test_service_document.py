# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from swh.deposit.tests import TEST_CONFIG
from swh.deposit.config import SD_IRI
from ..common import BasicTestCase, WithAuthTestCase


class ServiceDocumentNoAuthCase(APITestCase, BasicTestCase):
    """Service document endpoints are protected with basic authentication.

    """
    def test_service_document_no_authentication_fails(self):
        """Without authentication, service document endpoint should return 401

        """
        url = reverse(SD_IRI)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_service_document_with_http_accept_should_not_break(self):
        """Without auth, sd endpoint through browser should return 401

        """
        url = reverse(SD_IRI)

        # when
        response = self.client.get(
            url,
            HTTP_ACCEPT='text/html,application/xml;q=9,*/*,q=8')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ServiceDocumentCase(APITestCase, WithAuthTestCase, BasicTestCase):
    def assertResponseOk(self, response):  # noqa: N802
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content.decode('utf-8'),
                          '''<?xml version="1.0" ?>
<service xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:sword="http://purl.org/net/sword/terms/"
    xmlns:atom="http://www.w3.org/2005/Atom"
    xmlns="http://www.w3.org/2007/app">

    <sword:version>2.0</sword:version>
    <sword:maxUploadSize>%s</sword:maxUploadSize>

    <workspace>
        <atom:title>The Software Heritage (SWH) Archive</atom:title>
        <collection href="http://testserver/1/%s/">
            <atom:title>%s Software Collection</atom:title>
            <accept>application/zip</accept>
            <accept>application/x-tar</accept>
            <sword:collectionPolicy>Collection Policy</sword:collectionPolicy>
            <dcterms:abstract>Software Heritage Archive</dcterms:abstract>
            <sword:treatment>Collect, Preserve, Share</sword:treatment>
            <sword:mediation>false</sword:mediation>
            <sword:metadataRelevantHeader>false</sword:metadataRelevantHeader>
            <sword:acceptPackaging>http://purl.org/net/sword/package/SimpleZip</sword:acceptPackaging>
            <sword:service>http://testserver/1/%s/</sword:service>
            <sword:name>%s</sword:name>
        </collection>
    </workspace>
</service>
''' % (TEST_CONFIG['max_upload_size'],
       self.username,
       self.username,
       self.username,
       self.username))  # noqa

    def test_service_document(self):
        """With authentication, service document list user's collection

        """
        url = reverse(SD_IRI)

        # when
        response = self.client.get(url)

        # then
        self.assertResponseOk(response)

    def test_service_document_with_http_accept_header(self):
        """With authentication, with browser, sd list user's collection

        """
        url = reverse(SD_IRI)

        # when
        response = self.client.get(
            url,
            HTTP_ACCEPT='text/html,application/xml;q=9,*/*,q=8')

        self.assertResponseOk(response)
