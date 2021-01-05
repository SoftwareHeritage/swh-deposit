# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import hashlib
from io import BytesIO
import os
import re
import tarfile
import tempfile

from django.core.files.uploadedfile import InMemoryUploadedFile

from swh.core import tarball


def compute_info(archive_path):
    """Given a path, compute information on path.

    """
    with open(archive_path, "rb") as f:
        length = 0
        sha1sum = hashlib.sha1()
        md5sum = hashlib.md5()
        data = b""
        for chunk in f:
            sha1sum.update(chunk)
            md5sum.update(chunk)
            length += len(chunk)
            data += chunk

    return {
        "dir": os.path.dirname(archive_path),
        "name": os.path.basename(archive_path),
        "path": archive_path,
        "length": length,
        "sha1sum": sha1sum.hexdigest(),
        "md5sum": md5sum.hexdigest(),
        "data": data,
    }


def _compress(path, extension, dir_path):
    """Compress path according to extension

    """
    if extension == "zip" or extension == "tar":
        return tarball.compress(path, extension, dir_path)
    elif "." in extension:
        split_ext = extension.split(".")
        if split_ext[0] != "tar":
            raise ValueError(
                "Development error, only zip or tar archive supported, "
                "%s not supported" % extension
            )

        # deal with specific tar
        mode = split_ext[1]
        supported_mode = ["xz", "gz", "bz2"]
        if mode not in supported_mode:
            raise ValueError(
                "Development error, only %s supported, %s not supported"
                % (supported_mode, mode)
            )
        files = tarball._ls(dir_path)
        with tarfile.open(path, "w:%s" % mode) as t:
            for fpath, fname in files:
                t.add(fpath, arcname=fname, recursive=False)

        return path


def create_arborescence_archive(
    root_path, archive_name, filename, content, up_to_size=None, extension="zip"
):
    """Build an archive named archive_name in the root_path.
    This archive contains one file named filename with the content content.

    Args:
        root_path (str): Location path of the archive to create
        archive_name (str): Archive's name (without extension)
        filename (str): Archive's content is only one filename
        content (bytes): Content of the filename
        up_to_size (int | None): Fill in the blanks size to oversize
          or complete an archive's size
        extension (str): Extension of the archive to write (default is zip)

    Returns:
        dict with the keys:
        - dir: the directory of that archive
        - path: full path to the archive
        - sha1sum: archive's sha1sum
        - length: archive's length

    """
    os.makedirs(root_path, exist_ok=True)
    archive_path_dir = tempfile.mkdtemp(dir=root_path)

    dir_path = os.path.join(archive_path_dir, archive_name)
    os.mkdir(dir_path)

    filepath = os.path.join(dir_path, filename)
    _length = len(content)
    count = 0
    batch_size = 128
    with open(filepath, "wb") as f:
        f.write(content)
        if up_to_size:  # fill with blank content up to a given size
            count += _length
            while count < up_to_size:
                f.write(b"0" * batch_size)
                count += batch_size

    _path = "%s.%s" % (dir_path, extension)
    _path = _compress(_path, extension, dir_path)
    return compute_info(_path)


def create_archive_with_archive(root_path, name, archive):
    """Create an archive holding another.

    """
    invalid_archive_path = os.path.join(root_path, name)
    with tarfile.open(invalid_archive_path, "w:gz") as _archive:
        _archive.add(archive["path"], arcname=archive["name"])
    return compute_info(invalid_archive_path)


def check_archive(archive_name: str, archive_name_to_check: str):
    """Helper function to ensure archive_name is present within the
       archive_name_to_check.

    Raises:
        AssertionError if archive_name is not present within
            archive_name_to_check

    """
    ARCHIVE_FILEPATH_PATTERN = re.compile(
        r"client_[0-9].*/[0-9]{8}-[0-9]{6}\.[0-9]{6}/[a-zA-Z0-9.].*"
    )
    assert ARCHIVE_FILEPATH_PATTERN.match(archive_name_to_check)

    if "." in archive_name:
        filename, extension = archive_name.split(".")
        pattern = re.compile(".*/%s.*\\.%s" % (filename, extension))
    else:
        pattern = re.compile(".*/%s" % archive_name)
    assert pattern.match(archive_name_to_check) is not None


def _post_or_put_archive(f, url, archive, slug=None, in_progress=None, **kwargs):
    default_kwargs = dict(
        content_type="application/zip",
        CONTENT_LENGTH=archive["length"],
        HTTP_CONTENT_DISPOSITION="attachment; filename=%s" % (archive["name"],),
        HTTP_PACKAGING="http://purl.org/net/sword/package/SimpleZip",
    )
    kwargs = {**default_kwargs, **kwargs}
    return f(url, data=archive["data"], HTTP_CONTENT_MD5=archive["md5sum"], **kwargs,)


def post_archive(authenticated_client, *args, **kwargs):
    return _post_or_put_archive(authenticated_client.post, *args, **kwargs)


def put_archive(authenticated_client, *args, **kwargs):
    return _post_or_put_archive(authenticated_client.put, *args, **kwargs)


def post_atom(authenticated_client, url, data, **kwargs):
    return authenticated_client.post(
        url, content_type="application/atom+xml;type=entry", data=data, **kwargs
    )


def put_atom(authenticated_client, url, data, **kwargs):
    return authenticated_client.put(
        url, content_type="application/atom+xml;type=entry", data=data, **kwargs
    )


def _post_or_put_multipart(f, url, archive, atom_entry, **kwargs):
    archive = InMemoryUploadedFile(
        BytesIO(archive["data"]),
        field_name=archive["name"],
        name=archive["name"],
        content_type="application/x-tar",
        size=archive["length"],
        charset=None,
    )

    atom_entry = InMemoryUploadedFile(
        BytesIO(atom_entry.encode("utf-8")),
        field_name="atom0",
        name="atom0",
        content_type='application/atom+xml; charset="utf-8"',
        size=len(atom_entry),
        charset="utf-8",
    )

    return f(
        url,
        format="multipart",
        data={"archive": archive, "atom_entry": atom_entry,},
        **kwargs,
    )


def post_multipart(authenticated_client, *args, **kwargs):
    return _post_or_put_multipart(authenticated_client.post, *args, **kwargs)


def put_multipart(authenticated_client, *args, **kwargs):
    return _post_or_put_multipart(authenticated_client.put, *args, **kwargs)
