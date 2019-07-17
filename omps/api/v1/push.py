#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

from functools import partial
import logging
import os
from tempfile import NamedTemporaryFile, TemporaryDirectory
import zipfile

from flask import jsonify, current_app, request
from yaml import safe_load

from . import API
from omps.api.common import extract_auth_token, replace_registries
from omps.constants import (
    ALLOWED_EXTENSIONS,
    DEFAULT_ZIPFILE_MAX_UNCOMPRESSED_SIZE,
)
from omps.errors import (
    OMPSInvalidVersionFormat,
    OMPSUploadedFileError,
    OMPSExpectedFileError,
    PackageValidationError,
    QuayPackageNotFound,
)
from omps.greenwave import GREENWAVE
from omps.koji_util import KOJI
from omps.quay import ReleaseVersion, ORG_MANAGER

logger = logging.getLogger(__name__)


def validate_allowed_extension(filename):
    """Check file extension"""
    _, extension = os.path.splitext(filename)
    if extension.lower() not in ALLOWED_EXTENSIONS:
        raise OMPSUploadedFileError(
            'Uploaded file extension "{}" is not any of {}'.format(
                extension, ALLOWED_EXTENSIONS))


def _extract_zip_file(
    filepath, target_dir,
    max_uncompressed_size=DEFAULT_ZIPFILE_MAX_UNCOMPRESSED_SIZE
):
    """Extract zip file into target directory

    :param filepath: path to zip archive file
    :param target_dir: directory where extracted files will be stored
    :param max_uncompressed_size: size in Bytes how big data can be accepted
        after uncompressing
    """
    try:
        archive = zipfile.ZipFile(filepath)
    except zipfile.BadZipFile as e:
        raise OMPSUploadedFileError(str(e))

    if logger.isEnabledFor(logging.DEBUG):
        # log content of zipfile
        logger.debug(
            'Content of zip archive:\n%s',
            '\n'.join(
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

    try:
        bad_file = archive.testzip()
    except RuntimeError as e:
        # trying to open an encrypted zip file without a password
        raise OMPSUploadedFileError(str(e))

    if bad_file is not None:
        raise OMPSUploadedFileError(
            "CRC check failed for file {} in archive".format(bad_file)
        )
    archive.extractall(target_dir)
    archive.close()


def extract_zip_file_from_request(
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

    with NamedTemporaryFile('w', suffix='.zip') as tmpf:
        uploaded_file.save(tmpf.name)
        _extract_zip_file(tmpf.name, target_dir,
                          max_uncompressed_size=max_uncompressed_size)


def extract_zip_file_from_koji(
    nvr, target_dir,
    max_uncompressed_size=DEFAULT_ZIPFILE_MAX_UNCOMPRESSED_SIZE
):
    """Store content of operators_manifests zipfile in target_dir

    :param nvr: N-V-R of koji build
    :param target_dir: directory where extracted files will be stored
    :param max_uncompressed_size: size in Bytes how big data can be accepted
        after uncompressing
    """
    with NamedTemporaryFile('wb', suffix='.zip') as tmpf:
        KOJI.download_manifest_archive(nvr, tmpf)
        if GREENWAVE.enabled:
            GREENWAVE.check_build(nvr)
        _extract_zip_file(tmpf.name, target_dir,
                          max_uncompressed_size=max_uncompressed_size)


def get_package_version(quay_org, repo, version=None):
    """Returns version of new release.
    If version is passed, it will be validated
    If no version is passed then quay repo is queried for versions and latest
    version is incremented by 1 on major position.

    :param QuayOrganization quay_org: Quay organization object
    :param str repo: repository name
    :param str|None version:
    :rtype: str
    :return: version to be used as release
    """
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


def _get_reponame_from_manifests(source_dir):
    for filename in os.listdir(source_dir):
        filename = os.path.join(source_dir, filename)
        if filename.endswith('.yaml') or filename.endswith('.yml'):
            with open(filename, 'r') as f:
                contents = safe_load(f.read())
                if 'packageName' in contents:
                    name = contents['packageName']
                    logger.info("Found packageName %r in %r", name, filename)
                    return name

    raise PackageValidationError("Could not find packageName in manifests.")


def _dir_files(dir_path):
    res_files = []
    for root, dirs, files in os.walk(dir_path):
        for fname in files:
            file_relpath = os.path.relpath(
                os.path.join(root, fname), start=dir_path)
            res_files.append(file_relpath)
    return sorted(res_files)


def _zip_flow(*, organization, repo, version, extract_manifest_func,
              extras_data=None):
    """
    :param str organization: quay.io organization
    :param str|None repo: target repository (if not specified, will be taken
         from manifest data)
    :param str|None version: version of operator manifest
    :param Callable[str, int] extract_manifest_func: function to retrieve operator
        manifests zip file. First argument of function is path to target dir
        where zip archive content will be extracted, second argument max size
        of extracted files
    :param extras_data: extra data added to response
    :return: JSON response
    """
    cnr_token = extract_auth_token(request)
    quay_org = ORG_MANAGER.get_org(organization, cnr_token)

    data = {}

    with TemporaryDirectory() as tmpdir:
        max_size = current_app.config['ZIPFILE_MAX_UNCOMPRESSED_SIZE']
        extract_manifest_func(tmpdir, max_uncompressed_size=max_size)
        extracted_files = _dir_files(tmpdir)
        logger.info("Extracted files: %s", extracted_files)
        data['extracted_files'] = extracted_files

        if repo is None:
            repo = _get_reponame_from_manifests(tmpdir)

        version = get_package_version(quay_org, repo, version)
        logger.info("Using release version: %s", version)

        replace_registries(quay_org, tmpdir)

        quay_org.push_operator_manifest(repo, version, tmpdir)

    data.update({
        'organization': organization,
        'repo': repo,
        'version': version,
    })
    if extras_data:
        data.update(extras_data)

    resp = jsonify(data)
    resp.status_code = 200
    return resp


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
    return _zip_flow(
        organization=organization,
        repo=repo,
        version=version,
        extract_manifest_func=partial(extract_zip_file_from_request, request)
    )


@API.route("/<organization>/<repo>/koji/<nvr>", defaults={"version": None},
           methods=('POST',))
@API.route("/<organization>/<repo>/koji/<nvr>/<version>", methods=('POST',))
def push_koji_nvr(organization, repo, nvr, version):
    """
    Get operator manifest from koji by specified NVR and upload operator
    manifest to registry
    :param organization: quay.io organization
    :param repo: target repository
    :param nvr: image NVR from koji
    """
    return _zip_flow(
        organization=organization,
        repo=repo,
        version=version,
        extract_manifest_func=partial(extract_zip_file_from_koji, nvr),
        extras_data={'nvr': nvr}
    )
