Retrieve status
^^^^^^^^^^^^^^^^

.. http:get:: /1/<collection-name>/<deposit-id>/

    Returns deposit's status.

    The different statuses:

    - **partial**: multipart deposit is still ongoing
    - **deposited**: deposit completed, ready for checks
    - **rejected**: deposit failed the checks
    - **verified**: content and metadata verified, ready for loading
    - **loading**: loading in-progress
    - **done**: loading completed successfully
    - **failed**: the deposit loading has failed

    Also known as STATE-IRI

    :param text <name><pass>: the client's credentials
    :statuscode 201: with the deposit's status
    :statuscode 401: Unauthorized
    :statuscode 404: access to an unknown deposit


Rejected deposit
~~~~~~~~~~~~~~~~

It so happens that deposit could be rejected.  In that case, the
`deposit_status_detail` entry will explain failed checks.

Many reasons are possibles, here are some:

- Deposit without software archive (main goal of the deposit is to
  deposit software source code)

- Deposit with malformed software archive (i.e archive within archive)

- Deposit with invalid software archive (corrupted archive, although,
  this one should happen during upload and not during checks)

- Deposit with unsupported archive format

- Deposit with missing metadata


Sample response
~~~~~~~~~~~~~~~

    Successful deposit:

    .. code:: xml

        <entry xmlns="http://www.w3.org/2005/Atom"
               xmlns:sword="http://purl.org/net/sword/"
               xmlns:dcterms="http://purl.org/dc/terms/">
            <deposit_id>160</deposit_id>
            <deposit_status>done</deposit_status>
            <deposit_status_detail>The deposit has been successfully loaded into the Software Heritage archive</deposit_status_detail>
            <deposit_swh_id>swh:1:dir:d83b7dda887dc790f7207608474650d4344b8df9</deposit_swh_id>
            <deposit_swh_id_context>swh:1:dir:d83b7dda887dc790f7207608474650d4344b8df9;origin=https://forge.softwareheritage.org/source/jesuisgpl/</deposit_swh_id>
            <deposit_swh_anchor_id>swh:1:rev:e76ea49c9ffbb7f73611087ba6e999b19e5d71eb</deposit_swh_id>
            <deposit_swh_anchor_id_context>swh:1:rev:e76ea49c9ffbb7f73611087ba6e999b19e5d71eb;origin=https://forge.softwareheritage.org/source/jesuisgpl/</deposit_swh_id>
        </entry>

    Rejected deposit:

    .. code:: xml

        <entry xmlns="http://www.w3.org/2005/Atom"
               xmlns:sword="http://purl.org/net/sword/"
               xmlns:dcterms="http://purl.org/dc/terms/">
            <deposit_id>148</deposit_id>
            <deposit_status>rejected</deposit_status>
            <deposit_status_detail>- At least one url field must be compatible with the client&#39;s domain name (codemeta:url)</deposit_status_detail>
        </entry>