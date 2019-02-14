#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#
import logging
import os
from tempfile import NamedTemporaryFile, TemporaryDirectory
import zipfile

from flask import Blueprint, jsonify, current_app, request

from .constants import (
    ALLOWED_EXTENSIONS,
    DEFAULT_ZIPFILE_MAX_UNCOMPRESSED_SIZE,
    DEFAULT_RELEASE_VERSION,
)
from .errors import OMPSUploadedFileError, OMPSExpectedFileError

logger = logging.getLogger(__name__)
BLUEPRINT = Blueprint('push', __name__)


def validate_allowed_extension(filename):
    """Check file extension"""
    _, extension = os.path.splitext(filename)
    if extension.lower() not in ALLOWED_EXTENSIONS:
        raise OMPSUploadedFileError(
            'Uploaded file extension "{}" is not any of {}'.format(
                extension, ALLOWED_EXTENSIONS))


def extract_zip_file(
    req, target_dir,
    max_uncompressed_size=DEFAULT_ZIPFILE_MAX_UNCOMPRESSED_SIZE
):
    """Store uploaded file in target_directory

    :param req: Flask request object
    :param target_dir: directory where file will be stored
    :param max_uncompressed_size: size in Bytes how big data can be accepted
        after uncompressing
    """
    assert req.method == 'POST'
    if 'file' not in req.files:
        raise OMPSExpectedFileError('No field "file" in uploaded data')
    uploaded_file = req.files['file']
    if not uploaded_file.filename:
        # from Flask docs:
        #   if user does not select file, browser also
        #   submit an empty part without filename
        raise OMPSExpectedFileError('No selected "file" in uploaded data')

    validate_allowed_extension(uploaded_file.filename)

    with NamedTemporaryFile('w', suffix='.zip', dir=target_dir) as tmpf:
        uploaded_file.save(tmpf.name)
        try:
            archive = zipfile.ZipFile(tmpf.name)
        except zipfile.BadZipFile as e:
            raise OMPSUploadedFileError(str(e))

        if logger.isEnabledFor(logging.DEBUG):
            # log content of zipfile
            logger.debug(
                'Content of uploaded zip archive "%s":\n%s',
                uploaded_file.filename, '\n'.join(
                    "name={zi.filename}, compress_size={zi.compress_size}, "
                    "file_size={zi.file_size}".format(zi=zipinfo)
                    for zipinfo in archive.filelist
                )
            )

        uncompressed_size = sum(zi.file_size for zi in archive.filelist)
        if uncompressed_size > max_uncompressed_size:
            raise OMPSUploadedFileError(
                "Uncompressed archive is larger than limit "
                "({}B>{}B)".format(
                    uncompressed_size, max_uncompressed_size
                ))

        bad_file = archive.testzip()
        if bad_file is not None:
            raise OMPSUploadedFileError(
                "CRC check failed for file {} in archive".format(bad_file)
            )
        archive.extractall(target_dir)
        archive.close()


@BLUEPRINT.route("/<organization>/<repo>/zipfile/<version>", methods=('POST',))
def push_zipfile_with_version(organization, repo, version):
    """
    Push the particular version of operator manifest to registry from
    the uploaded zipfile

    :param organization: quay.io organization
    :param repo: target repository
    :param version: version of operator manifest
    """
    data = {
        'organization': organization,
        'repo': repo,
        'version': version,
        'msg': 'Not Implemented. Testing only'
    }

    with TemporaryDirectory() as tmpdir:
        max_size = current_app.config['ZIPFILE_MAX_UNCOMPRESSED_SIZE']
        extract_zip_file(request, tmpdir,
                         max_uncompressed_size=max_size)
        data['extracted_files'] = os.listdir(tmpdir)
    resp = jsonify(data)
    resp.status_code = 200
    return resp


@BLUEPRINT.route("/<organization>/<repo>/zipfile", methods=('POST',))
def push_zipfile(organization, repo):
    """
    Push operator manifest to registry from uploaded zipfile

    :param organization: quay.io organization
    :param repo: target repository
    """
    version = DEFAULT_RELEASE_VERSION
    return push_zipfile_with_version(organization, repo, version)


@BLUEPRINT.route("/<organization>/<repo>/koji/<nvr>", methods=('POST',))
def push_koji_nvr(organization, repo, nvr):
    """
    Get operator manifest from koji by specified NVR and upload operator
    manifest to registry
    :param organization: quay.io organization
    :param repo: target repository
    :param nvr: image NVR from koji
    """
    data = {
        'organization': organization,
        'repo': repo,
        'nvr': nvr,
        'msg': 'Not Implemented. Testing only'
    }
    resp = jsonify(data)
    resp.status_code = 200
    return resp
