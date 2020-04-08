# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.urls import reverse
from rest_framework import status

from swh.deposit.config import SD_IRI


def test_service_document_no_auth_fails(client):
    """Without authentication, service document endpoint should return 401

    """
    url = reverse(SD_IRI)
    response = client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_service_document_no_auth_with_http_auth_should_not_break(client):
    """Without auth, sd endpoint through browser should return 401

    """
    url = reverse(SD_IRI)
    response = client.get(url, HTTP_ACCEPT="text/html,application/xml;q=9,*/*,q=8")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_service_document(authenticated_client, deposit_user):
    """With authentication, service document list user's collection

    """
    url = reverse(SD_IRI)
    response = authenticated_client.get(url)
    check_response(response, deposit_user.username)


def test_service_document_with_http_accept_header(authenticated_client, deposit_user):
    """With authentication, with browser, sd list user's collection

    """
    url = reverse(SD_IRI)
    response = authenticated_client.get(
        url, HTTP_ACCEPT="text/html,application/xml;q=9,*/*,q=8"
    )
    check_response(response, deposit_user.username)


def check_response(response, username):
    assert response.status_code == status.HTTP_200_OK
    assert (
        response.content.decode("utf-8")
        == """<?xml version="1.0" ?>
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
"""
        % (500, username, username, username, username)
    )  # noqa
