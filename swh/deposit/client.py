# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""Module in charge of defining an swh-deposit client

"""

from abc import ABCMeta, abstractmethod
import hashlib
import logging
import os
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urljoin
import warnings

import requests

from swh.core.config import load_from_envvar
from swh.deposit import __version__ as swh_deposit_version
from swh.deposit.utils import parse_xml

logger = logging.getLogger(__name__)


def compute_unified_information(
    collection: str,
    in_progress: bool,
    slug: str,
    *,
    filepath: Optional[str] = None,
    swhid: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Given a filepath, compute necessary information on that file.

    Args:
        collection: Deposit collection
        in_progress: do we finalize the deposit?
        slug: external id to use
        filepath: Path to the file to compute the necessary information out of
        swhid: Deposit swhid if any

    Returns:
        dict with keys:

            'slug': external id to use
            'in_progress': do we finalize the deposit?
            'content-type': content type associated
            'md5sum': md5 sum
            'filename': filename
            'filepath': filepath
            'swhid': deposit swhid

    """
    result: Dict[str, Any] = {
        "slug": slug,
        "in_progress": in_progress,
        "swhid": swhid,
    }
    content_type: Optional[str] = None
    md5sum: Optional[str] = None

    if filepath:
        filename = os.path.basename(filepath)
        md5sum = hashlib.md5(open(filepath, "rb").read()).hexdigest()
        extension = filename.split(".")[-1]
        if "zip" in extension:
            content_type = "application/zip"
        else:
            content_type = "application/x-tar"
        result.update(
            {
                "content-type": content_type,
                "md5sum": md5sum,
                "filename": filename,
                "filepath": filepath,
            }
        )

    return result


class MaintenanceError(ValueError):
    """Informational maintenance error exception

    """

    pass


def handle_deprecated_config(config: Dict) -> Tuple[str, Optional[Tuple[str, str]]]:
    warnings.warn(
        '"config" argument is deprecated, please '
        'use "url" and "auth" arguments instead; note that "auth" '
        "expects now a couple (username, password) and not a dict.",
        DeprecationWarning,
    )
    url: str = config["url"]
    auth: Optional[Tuple[str, str]] = None

    if config.get("auth"):
        auth = (config["auth"]["username"], config["auth"]["password"])

    return (url, auth)


class BaseApiDepositClient:
    """Deposit client base class

    """

    def __init__(
        self,
        config: Optional[Dict] = None,
        url: Optional[str] = None,
        auth: Optional[Tuple[str, str]] = None,
    ):
        if not url and not config:
            config = load_from_envvar()
        if config:
            url, auth = handle_deprecated_config(config)

        # needed to help mypy not be fooled by the Optional nature of url
        assert url is not None

        self.base_url = url.strip("/") + "/"
        self.auth = auth
        self.session = requests.Session()
        if auth:
            self.session.auth = auth
        self.session.headers.update(
            {"user-agent": f"swh-deposit/{swh_deposit_version}"}
        )

    def do(self, method, url, *args, **kwargs):
        """Internal method to deal with requests, possibly with basic http
           authentication.

        Args:
            method (str): supported http methods as in self._methods' keys

        Returns:
            The request's execution

        """
        full_url = urljoin(self.base_url, url.lstrip("/"))
        return self.session.request(method, full_url, *args, **kwargs)


class PrivateApiDepositClient(BaseApiDepositClient):
    """Private API deposit client to:

    - read a given deposit's archive(s)
    - read a given deposit's metadata
    - update a given deposit's status

    """

    def archive_get(self, archive_update_url, archive):
        """Retrieve the archive from the deposit to a local directory.

        Args:
            archive_update_url (str): The full deposit archive(s)'s raw content
                               to retrieve locally

            archive (str): the local archive's path where to store
            the raw content

        Returns:
            The archive path to the local archive to load.
            Or None if any problem arose.

        """
        r = self.do("get", archive_update_url, stream=True)
        if r.ok:
            with open(archive, "wb") as f:
                for chunk in r.iter_content():
                    f.write(chunk)

            return archive

        msg = "Problem when retrieving deposit archive at %s" % (archive_update_url,)
        logger.error(msg)

        raise ValueError(msg)

    def metadata_get(self, metadata_url):
        """Retrieve the metadata information on a given deposit.

        Args:
            metadata_url (str): The full deposit metadata url to retrieve
            locally

        Returns:
            The dictionary of metadata for that deposit or None if any
            problem arose.

        """
        r = self.do("get", metadata_url)
        if r.ok:
            return r.json()

        msg = "Problem when retrieving metadata at %s" % metadata_url
        logger.error(msg)

        raise ValueError(msg)

    def status_update(
        self,
        update_status_url,
        status,
        revision_id=None,
        directory_id=None,
        origin_url=None,
    ):
        """Update the deposit's status.

        Args:
            update_status_url (str): the full deposit's archive
            status (str): The status to update the deposit with
            revision_id (str/None): the revision's identifier to update to
            directory_id (str/None): the directory's identifier to update to
            origin_url (str/None): deposit's associated origin url

        """
        payload = {"status": status}
        if revision_id:
            payload["revision_id"] = revision_id
        if directory_id:
            payload["directory_id"] = directory_id
        if origin_url:
            payload["origin_url"] = origin_url

        self.do("put", update_status_url, json=payload)

    def check(self, check_url):
        """Check the deposit's associated data (metadata, archive(s))

        Args:
            check_url (str): the full deposit's check url

        """
        r = self.do("get", check_url)
        if r.ok:
            data = r.json()
            return data["status"]

        msg = "Problem when checking deposit %s" % check_url
        logger.error(msg)

        raise ValueError(msg)


class BaseDepositClient(BaseApiDepositClient, metaclass=ABCMeta):
    """Base Deposit client to access the public api.

    """

    def __init__(
        self, config=None, url=None, auth=None, error_msg=None, empty_result={}
    ):
        super().__init__(url=url, auth=auth, config=config)
        self.error_msg = error_msg
        self.empty_result = empty_result

    @abstractmethod
    def compute_url(self, *args, **kwargs):
        """Compute api url endpoint to query."""
        pass

    @abstractmethod
    def compute_method(self, *args, **kwargs):
        """Http method to use on the url"""
        pass

    @abstractmethod
    def parse_result_ok(self, xml_content):
        """Given an xml result from the api endpoint, parse it and returns a
           dict.

        """
        pass

    def compute_information(self, *args, **kwargs) -> Dict[str, Any]:
        """Compute some more information given the inputs (e.g http headers,
           ...)

        """
        return {}

    def parse_result_error(self, xml_content):
        """Given an error response in xml, parse it into a dict.

        Returns:
            dict with following keys:

                'error': The error message
                'detail': Some more detail about the error if any

        """
        data = parse_xml(xml_content)
        return {
            "summary": data["summary"],
            "detail": data["detail"],
            "sword:verboseDescription": data["sword:verboseDescription"],
        }

    def do_execute(self, method, url, info):
        """Execute the http query to url using method and info information.

        By default, execute a simple query to url with the http
        method.  Override this in daughter class to improve the
        default behavior if needed.

        """
        return self.do(method, url)

    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """Main endpoint to prepare and execute the http query to the api.

        Raises:
            MaintenanceError if some api maintenance is happening.

        Returns:
            Dict of computed api data

        """
        url = self.compute_url(*args, **kwargs)
        method = self.compute_method(*args, **kwargs)
        info = self.compute_information(*args, **kwargs)

        try:
            r = self.do_execute(method, url, info)
        except Exception as e:
            msg = self.error_msg % (url, e)
            r = self.empty_result
            r.update(
                {"error": msg,}
            )
            return r
        else:
            if r.ok:
                if int(r.status_code) == 204:  # 204 returns no body
                    return {"status": r.status_code}
                else:
                    return self.parse_result_ok(r.text)
            else:
                error = self.parse_result_error(r.text)
                empty = self.empty_result
                error.update(empty)
                if r.status_code == 503:
                    summary = error.get("summary")
                    detail = error.get("sword:verboseDescription")
                    # Maintenance error
                    if summary and detail:
                        raise MaintenanceError(f"{summary}: {detail}")
                error.update(
                    {"status": r.status_code,}
                )
                return error


class ServiceDocumentDepositClient(BaseDepositClient):
    """Service Document information retrieval.

    """

    def __init__(self, config=None, url=None, auth=None):
        super().__init__(
            url=url,
            auth=auth,
            config=config,
            error_msg="Service document failure at %s: %s",
            empty_result={"collection": None},
        )

    def compute_url(self, *args, **kwargs):
        return "/servicedocument/"

    def compute_method(self, *args, **kwargs):
        return "get"

    def parse_result_ok(self, xml_content):
        """Parse service document's success response.

        """
        return parse_xml(xml_content)


class StatusDepositClient(BaseDepositClient):
    """Status information on a deposit.

    """

    def __init__(self, config=None, url=None, auth=None):
        super().__init__(
            url=url,
            auth=auth,
            config=config,
            error_msg="Status check failure at %s: %s",
            empty_result={
                "deposit_status": None,
                "deposit_status_detail": None,
                "deposit_swh_id": None,
            },
        )

    def compute_url(self, collection, deposit_id):
        return "/%s/%s/status/" % (collection, deposit_id)

    def compute_method(self, *args, **kwargs):
        return "get"

    def parse_result_ok(self, xml_content):
        """Given an xml content as string, returns a deposit dict.

        """
        data = parse_xml(xml_content)
        keys = [
            "deposit_id",
            "deposit_status",
            "deposit_status_detail",
            "deposit_swh_id",
            "deposit_swh_id_context",
            "deposit_external_id",
        ]
        return {key: data.get("swh:" + key) for key in keys}


class BaseCreateDepositClient(BaseDepositClient):
    """Deposit client base class to post new deposit.

    """

    def __init__(self, config=None, url=None, auth=None):
        super().__init__(
            url=url,
            auth=auth,
            config=config,
            error_msg="Post Deposit failure at %s: %s",
            empty_result={"swh:deposit_id": None, "swh:deposit_status": None,},
        )

    def compute_url(self, collection, *args, **kwargs):
        return "/%s/" % collection

    def compute_method(self, *args, **kwargs):
        return "post"

    def parse_result_ok(self, xml_content):
        """Given an xml content as string, returns a deposit dict.

        """
        data = parse_xml(xml_content)
        keys = [
            "deposit_id",
            "deposit_status",
            "deposit_status_detail",
            "deposit_date",
        ]
        return {key: data.get("swh:" + key) for key in keys}

    def compute_headers(self, info: Dict[str, Any]) -> Dict[str, Any]:
        return info

    def do_execute(self, method, url, info):
        with open(info["filepath"], "rb") as f:
            return self.do(method, url, data=f, headers=info["headers"])


class CreateArchiveDepositClient(BaseCreateDepositClient):
    """Post an archive (binary) deposit client."""

    def compute_headers(self, info):
        headers = {
            "CONTENT_MD5": info["md5sum"],
            "IN-PROGRESS": str(info["in_progress"]),
            "CONTENT-TYPE": info["content-type"],
            "CONTENT-DISPOSITION": "attachment; filename=%s" % (info["filename"],),
        }
        if "slug" in info:
            headers["SLUG"] = info["slug"]
        return headers

    def compute_information(self, *args, **kwargs) -> Dict[str, Any]:
        info = compute_unified_information(
            *args, filepath=kwargs["archive_path"], **kwargs
        )
        info["headers"] = self.compute_headers(info)
        return info


class UpdateArchiveDepositClient(CreateArchiveDepositClient):
    """Update (add/replace) an archive (binary) deposit client."""

    def compute_url(self, collection, *args, deposit_id=None, **kwargs):
        return "/%s/%s/media/" % (collection, deposit_id)

    def compute_method(self, *args, replace=False, **kwargs):
        return "put" if replace else "post"


class CreateMetadataDepositClient(BaseCreateDepositClient):
    """Post a metadata deposit client."""

    def compute_headers(self, info):
        headers = {
            "IN-PROGRESS": str(info["in_progress"]),
            "CONTENT-TYPE": "application/atom+xml;type=entry",
        }
        if "slug" in info:
            headers["SLUG"] = info["slug"]
        return headers

    def compute_information(self, *args, **kwargs) -> Dict[str, Any]:
        info = compute_unified_information(
            *args, filepath=kwargs["metadata_path"], **kwargs
        )
        info["headers"] = self.compute_headers(info)
        return info


class UpdateMetadataOnPartialDepositClient(CreateMetadataDepositClient):
    """Update (add/replace) metadata on partial deposit scenario."""

    def compute_url(self, collection, *args, deposit_id=None, **kwargs):
        return f"/{collection}/{deposit_id}/metadata/"

    def compute_method(self, *args, replace: bool = False, **kwargs) -> str:
        return "put" if replace else "post"


class UpdateMetadataOnDoneDepositClient(CreateMetadataDepositClient):
    """Update metadata on "done" deposit. This requires the deposit swhid."""

    def compute_url(self, collection, *args, deposit_id=None, **kwargs):
        return f"/{collection}/{deposit_id}/atom/"

    def compute_headers(self, info: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "CONTENT-TYPE": "application/atom+xml;type=entry",
            "X_CHECK_SWHID": info["swhid"],
        }

    def compute_method(self, *args, **kwargs) -> str:
        return "put"


class CreateMetadataOnlyDepositClient(BaseCreateDepositClient):
    """Create metadata-only deposit."""

    def compute_information(self, *args, **kwargs) -> Dict[str, Any]:
        return {
            "headers": {"CONTENT-TYPE": "application/atom+xml;type=entry",},
            "filepath": kwargs["metadata_path"],
        }

    def parse_result_ok(self, xml_content):
        """Given an xml content as string, returns a deposit dict.

        """
        data = parse_xml(xml_content)
        keys = [
            "deposit_id",
            "deposit_status",
            "deposit_date",
        ]
        return {key: data.get("swh:" + key) for key in keys}


class CreateMultipartDepositClient(BaseCreateDepositClient):
    """Create a multipart deposit client."""

    def _multipart_info(self, info, info_meta):
        files = [
            (
                "file",
                (info["filename"], open(info["filepath"], "rb"), info["content-type"]),
            ),
            (
                "atom",
                (
                    info_meta["filename"],
                    open(info_meta["filepath"], "rb"),
                    "application/atom+xml",
                ),
            ),
        ]

        headers = {
            "CONTENT_MD5": info["md5sum"],
            "IN-PROGRESS": str(info["in_progress"]),
        }
        if "slug" in info:
            headers["SLUG"] = info["slug"]

        return files, headers

    def compute_information(self, *args, **kwargs) -> Dict[str, Any]:
        info = compute_unified_information(*args, filepath=kwargs["archive_path"],)
        info_meta = compute_unified_information(
            *args, filepath=kwargs["metadata_path"],
        )
        files, headers = self._multipart_info(info, info_meta)
        return {"files": files, "headers": headers}

    def do_execute(self, method, url, info):
        return self.do(method, url, files=info["files"], headers=info["headers"])


class UpdateMultipartDepositClient(CreateMultipartDepositClient):
    """Update a multipart deposit client."""

    def compute_url(self, collection, *args, deposit_id=None, **kwargs):
        return "/%s/%s/metadata/" % (collection, deposit_id)

    def compute_method(self, *args, replace=False, **kwargs):
        return "put" if replace else "post"


class PublicApiDepositClient(BaseApiDepositClient):
    """Public api deposit client."""

    def service_document(self):
        """Retrieve service document endpoint's information."""
        return ServiceDocumentDepositClient(url=self.base_url, auth=self.auth).execute()

    def deposit_status(self, collection: str, deposit_id: int):
        """Retrieve status information on a deposit."""
        return StatusDepositClient(url=self.base_url, auth=self.auth).execute(
            collection, deposit_id
        )

    def deposit_create(
        self,
        collection: str,
        slug: Optional[str],
        archive: Optional[str] = None,
        metadata: Optional[str] = None,
        in_progress: bool = False,
    ):
        """Create a new deposit (archive, metadata, both as multipart)."""
        if archive and not metadata:
            return CreateArchiveDepositClient(
                url=self.base_url, auth=self.auth
            ).execute(collection, in_progress, slug, archive_path=archive)
        elif not archive and metadata:
            return CreateMetadataDepositClient(
                url=self.base_url, auth=self.auth
            ).execute(collection, in_progress, slug, metadata_path=metadata)
        else:
            return CreateMultipartDepositClient(
                url=self.base_url, auth=self.auth
            ).execute(
                collection,
                in_progress,
                slug,
                archive_path=archive,
                metadata_path=metadata,
            )

    def deposit_update(
        self,
        collection: str,
        deposit_id: int,
        slug: Optional[str],
        archive: Optional[str] = None,
        metadata: Optional[str] = None,
        in_progress: bool = False,
        replace: bool = False,
        swhid: Optional[str] = None,
    ):
        """Update (add/replace) existing deposit (archive, metadata, both)."""
        r = self.deposit_status(collection, deposit_id)
        if "error" in r:
            return r

        status = r["deposit_status"]
        if swhid is None and status != "partial":
            return {
                "error": "You can only act on deposit with status 'partial'",
                "detail": f"The deposit {deposit_id} has status '{status}'",
                "deposit_status": status,
                "deposit_id": deposit_id,
            }
        if swhid is not None and status != "done":
            return {
                "error": "You can only update metadata on deposit with status 'done'",
                "detail": f"The deposit {deposit_id} has status '{status}'",
                "deposit_status": status,
                "deposit_id": deposit_id,
            }
        if archive and not metadata:
            r = UpdateArchiveDepositClient(url=self.base_url, auth=self.auth).execute(
                collection,
                in_progress,
                slug,
                deposit_id=deposit_id,
                archive_path=archive,
                replace=replace,
            )
        elif not archive and metadata and swhid is None:
            r = UpdateMetadataOnPartialDepositClient(
                url=self.base_url, auth=self.auth
            ).execute(
                collection,
                in_progress,
                slug,
                deposit_id=deposit_id,
                metadata_path=metadata,
                replace=replace,
            )
        elif not archive and metadata and swhid is not None:
            r = UpdateMetadataOnDoneDepositClient(
                url=self.base_url, auth=self.auth
            ).execute(
                collection,
                in_progress,
                slug,
                deposit_id=deposit_id,
                metadata_path=metadata,
                swhid=swhid,
            )
        else:
            r = UpdateMultipartDepositClient(url=self.base_url, auth=self.auth).execute(
                collection,
                in_progress,
                slug,
                deposit_id=deposit_id,
                archive_path=archive,
                metadata_path=metadata,
                replace=replace,
            )

        if "error" in r:
            return r
        return self.deposit_status(collection, deposit_id)

    def deposit_metadata_only(
        self, collection: str, metadata: Optional[str] = None,
    ):
        assert metadata is not None
        return CreateMetadataOnlyDepositClient(
            url=self.base_url, auth=self.auth
        ).execute(collection, metadata_path=metadata)
