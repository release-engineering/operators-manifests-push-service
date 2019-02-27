#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#
import logging
import os
from tempfile import NamedTemporaryFile, TemporaryDirectory
import zipfile

from flask import jsonify, current_app, request

from . import API
from omps.constants import (
    ALLOWED_EXTENSIONS,
    DEFAULT_ZIPFILE_MAX_UNCOMPRESSED_SIZE,
)
from omps.errors import (
    OMPSInvalidVersionFormat,
    OMPSUploadedFileError,
    OMPSExpectedFileError,
    QuayPackageNotFound,
)
from omps.quay import QUAY_ORG_MANAGER, ReleaseVersion

logger = logging.getLogger(__name__)


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


def _get_package_version(quay_org, repo, version=None):
    if version is None:
        try:
            latest_ver = quay_org.get_latest_release_version(repo)
        except QuayPackageNotFound:
            version = current_app.config['DEFAULT_RELEASE_VERSION']
        else:
            latest_ver.increment()
            version = str(latest_ver)
    else:
        try:
            ReleaseVersion.validate_version(version)
        except ValueError as e:
            raise OMPSInvalidVersionFormat(str(e))
    return version


@API.route("/<organization>/<repo>/zipfile", defaults={"version": None},
                 methods=('POST',))
@API.route("/<organization>/<repo>/zipfile/<version>", methods=('POST',))
def push_zipfile(organization, repo, version=None):
    """
    Push the particular version of operator manifest to registry from
    the uploaded zipfile

    :param organization: quay.io organization
    :param repo: target repository
    :param version: version of operator manifest
    """
    quay_org = QUAY_ORG_MANAGER.organization_login(organization)

    version = _get_package_version(quay_org, repo, version)
    logger.info("Using release version: %s", version)

    data = {
        'organization': organization,
        'repo': repo,
        'version': version,
    }

    with TemporaryDirectory() as tmpdir:
        max_size = current_app.config['ZIPFILE_MAX_UNCOMPRESSED_SIZE']
        extract_zip_file(request, tmpdir,
                         max_uncompressed_size=max_size)
        extracted_files = os.listdir(tmpdir)
        logger.info("Extracted files: %s", extracted_files)
        data['extracted_files'] = extracted_files

        quay_org.push_operator_manifest(repo, version, tmpdir)

    resp = jsonify(data)
    resp.status_code = 200
    return resp


@API.route("/<organization>/<repo>/koji/<nvr>", methods=('POST',))
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
