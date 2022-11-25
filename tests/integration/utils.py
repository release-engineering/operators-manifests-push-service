#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import os
import yaml
import koji
import requests
import tarfile
import zipfile
from tempfile import TemporaryDirectory


def load_test_env():
    """Test environment configuration.
    """
    with open('test.env.yaml') as f:
        env = yaml.safe_load(f)
    return env


test_env = load_test_env()


def make_bundle(bundle):
    """Make a bundle to be used by the tests.

    Args:
        bundle: either a bundle as a dictionary OR
                a nested bundle as concatenated files OR
                a path to a directory of a nested bundle.
    Returns:
        A FlatBundle or a string, which has the files of a nested bundle
        concatenated.

    Raises:
        AssertionError if the argument is of a type that is not handled.
    """
    if isinstance(bundle, dict):
        return FlatBundle(bundle)
    elif isinstance(bundle, str):
        b = bundle
        if os.path.isdir(bundle):
            b = concatenated_files(bundle)
        return b
    else:
        assert False


class FlatBundle():
    """Wrapper to ease working with flat-bundles.
    """
    FIELDS = ('clusterServiceVersions', 'customResourceDefinitions', 'packages')

    def __init__(self, bundle_dict):
        self.bundle_dict = bundle_dict

    def __eq__(self, other):
        o = other
        if isinstance(other, str):
            o = FlatBundle(yaml.safe_load(other))

        for field in FlatBundle.FIELDS:
            sd = yaml.safe_load(self.bundle_dict['data'][field])
            od = yaml.safe_load(o.bundle_dict['data'][field])

            assert isinstance(sd, list)
            assert isinstance(od, list)

            for element in sd:
                if element not in od:
                    return False

        return True

    def __contains__(self, text):
        for field in FlatBundle.FIELDS:
            if text in self.bundle_dict['data'][field]:
                return True

        return False


class OMPS:
    """OMPS service.

    Collects methods to work with the OMPS service.

    Attributes:
        _api_url: URL of the OMPS API. Including version, excluding trailing /.
        _headers: Headers to be used, when talking to Quay.
            No header will be set if None.
    """
    _ENDPOINTS = {
        'v1': {
            'upload': '{api}/{org}/{repo}/zipfile{version}',
            'fetch': '{api}/{org}/{repo}/koji/{nvr}{version}',
            'delete': '{api}/{org}/{repo}{version}'
        },
        'v2': {
            'upload': '{api}/{org}/zipfile{version}',
            'fetch': '{api}/{org}/koji/{nvr}{version}',
            'delete': '{api}/{org}/{repo}{version}'
        }
    }

    def __init__(self, api_url, quay_token=None):
        self._api_url = api_url
        self._headers = {'Authorization': quay_token} if quay_token else {}
        api_version = api_url.split('/')[-1]
        self._endpoints = OMPS._ENDPOINTS[api_version]

    def upload(self, organization, repo, archive, version=None,
               field='file'):
        """Create a new release for a package by uploading an archive.

        Args:
            repo: Repository where the new release is uploaded.
            organization: Name of the organization where the repo belongs.
            archive: Path of the archive to upload.
            version: Version to be used for this release.
                If None, OMPS will create it.

        Returns:
            A requests.Response object.
            http://docs.python-requests.org/en/master/api/#requests.Response

        Raises: None.
        """
        url = self._endpoints['upload'].format(
            api=self._api_url,
            org=organization,
            repo=repo,
            version='' if not version else '/' + version)
        files = {field: open(archive, 'rb')}

        return requests.post(url, files=files, headers=self._headers)

    def delete(self, organization, repo, version=None):
        """Delete one, more or all releases from a repo.

        Args:
            organization: Name of the organization where the repo belongs.
            repo: Repository from where the release will be deleted.
            version: Version to be deleted. If None, the repo will be cleaned up.

        Returns:
            A requests.Response object.
            http://docs.python-requests.org/en/master/api/#requests.Response

        Raises: None.
        """
        url = self._endpoints['delete'].format(
            api=self._api_url,
            org=organization,
            repo=repo,
            version='' if not version else '/' + version)

        return requests.delete(url, headers=self._headers)

    def fetch_nvr(self, organization, repo, nvr, version=None):
        """

        Args:

        Returns:

        Raises:
        """
        url = self._endpoints['fetch'].format(
            api=self._api_url,
            org=organization,
            repo=repo,
            nvr=nvr,
            version='' if not version else '/' + version)

        return requests.post(url, headers=self._headers)


class QuayAppRegistry:
    """Quay App Registry.

    Collects methods to work with the Quay App Registry.

    Note: The terminology used in this class (names and docs) are
        according to:
        https://github.com/operator-framework/go-appr/blob/master/appr.spec.yaml

    Attributes:
        _api_url: URL of the App Registry. Including version, excluding trailing /.
            Example: https://quay.io/api/v1
        _token: Authorization token retrieved after logging in with
            username .and password. None at construction time.
    """
    def __init__(self, quay_app_registry_api, quay_api=None, oauth_token=None):
        self._api_url = quay_app_registry_api
        self._quay_api = quay_api
        self._oauth_header = {
            'Authorization': f'Bearer {oauth_token}'
        } if oauth_token else None
        self._token = None
        self._cnr_header = None

    def login_to_cnr(self, username, password):
        """Login to Quay CNR endpoint and store the authorization header.

        Args:
            username, password: Credentials used to log in.

        Returns:
            None.

        Raises:
            HTTPError: Login failed.
        """
        data = {
            "user": {
                "username": username,
                "password": password
            },
        }
        url = f'{self._api_url}/users/login'

        r = requests.post(url, json=data)
        r.raise_for_status()

        self._token = r.json()['token']
        self._cnr_header = {'Authorization': self._token}

    @property
    def token(self):
        return self._token

    def get_releases(self, namespace, package, authorization=True):
        """Get all releases for a package.

        Args:
            namespace: Namespace.
            package: Package.
            authorization: If True, the Quay endpoint is accessed
                using the authorization token. If evaluates to False,
                the endpoint is accessed unauthorized. Defaults to True.

        Returns:
            List of dictionaries, representing releases. Empty list if the
            package is not found.
            Example:
                [
                    {
                        "content": {
                            "digest": "<64 hex chars>",
                            "mediaType": "application/vnd.cnr.package.helm.v0.tar+gzip",
                            "size": 1628,
                            "urls": []
                        },
                        "created_at": "2019-03-05T11:39:28",
                        "digest": "sha256:<64 hex chars>",
                        "mediaType": "application/vnd.cnr.package-manifest.helm.v0.json",
                        "metadata": null,
                        "package": "community-operators/etcd",
                        "release": "1.0.0"
                    }
                ]


        Raises:
            HTTPError: For all errors except 404 Not Found.
        """
        url = f'{self._api_url}/packages/{namespace}/{package}'
        headers = (authorization and self._cnr_header) or None

        r = requests.get(url, headers=headers)
        if r.status_code == requests.codes.not_found:
            return []
        else:
            r.raise_for_status()

        return r.json()

    def get_release(self, namespace, package, release, authorization=True):
        for rel in self.get_releases(namespace, package, authorization):
            if rel['release'] == release:
                return rel
        return {}

    def get_bundle(self, namespace, package, release, authorization=True):
        """Get all releases for a package.

        Args:
            namespace: Namespace.
            package: Package.
            releases: Release.
            authorization: If True, the Quay endpoint is accessed
                using the authorization token. If evaluates to False,
                the endpoint is accessed unauthorized. Defaults to True.

        Returns:
            An operator bundle dictionary, loaded from  the 'bundle.yaml'
            retrieved from Quay.

        Raises:
            HTTPError: when failed to retrieve the bundle.
        """
        url = '{api}/packages/{namespace}/{package}/{release}/{media_type}/pull'
        url = url.format(api=self._api_url, namespace=namespace,
                         package=package, release=release, media_type='helm')
        headers = (authorization and self._cnr_header) or None
        r = requests.get(url, headers=headers)
        r.raise_for_status()

        bundle = ''
        with TemporaryDirectory() as tempdir:
            archive = f'{tempdir}/operator.tar.gz'
            with open(archive, 'wb') as f:
                f.write(r.content)

            with tarfile.open(archive, 'r:gz') as tar:
                def is_within_directory(directory, target):
                    
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                
                    prefix = os.path.commonprefix([abs_directory, abs_target])
                    
                    return prefix == abs_directory
                
                def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                
                    for member in tar.getmembers():
                        member_path = os.path.join(path, member.name)
                        if not is_within_directory(path, member_path):
                            raise Exception("Attempted Path Traversal in Tar File")
                
                    tar.extractall(path, members, numeric_owner=numeric_owner) 
                    
                
                safe_extract(tar, path=tempdir)

            os.remove(archive)
            bundle_file = f"{tempdir}/bundle.yaml"
            if os.path.isfile(bundle_file):
                with open(bundle_file, 'r') as f:
                    bundle = yaml.safe_load(f)
            else:
                # Assume that this is a nested bundle. Concatenate the sorted
                # files in a single string.
                bundle = concatenated_files(tempdir)

        return bundle

    def get_packages(self, namespace, authorization=True):
        """Get all packages from a namespace.

        Args:
            namespace: Namespace.
            authorization: If True, the Quay endpoint is accessed
                using the authorization token. If evaluates to False,
                the endpoint is accessed unauthorized. Defaults to True.

        Returns:
            List of dictionaries, representing packages.
            Example:
                [
                    {
                        "channels": null,
                        "created_at": "2019-03-05T09:41:48",
                        "default": "1.0.0",
                        "manifests": [
                            "helm"
                        ],
                        "name": "community-operators/etcd",
                        "namespace": "community-operators",
                        "releases": [
                            "1.0.0"
                        ],
                        "updated_at": "2019-03-05T09:41:48",
                        "visibility": "public"
                    }
                ]

        Raises:
            HTTPError: Getting packages failed.
        """
        url = f'{self._api_url}/packages'
        headers = (authorization and self._cnr_header) or None
        payload = {'namespace': namespace}

        r = requests.get(url, headers=headers, params=payload)
        r.raise_for_status()

        return r.json()

    def delete_releases(self, name, releases, authorization=True):
        """Delete a list of releases from a package.

        Args:
            name: 'namespace/package' to delete releases from.
            releases: List of releases to delete.
            authorization: If True, the Quay endpoint is accessed
                using the authorization token. If evaluates to False,
                the endpoint is accessed unauthorized. Defaults to True.

        Returns:
            None

        Raises:
            HTTPError: Deleting a release failed.
        """
        package_url = f'{self._api_url}/packages/{name}'
        headers = (authorization and self._cnr_header) or None

        for release in releases:
            url = f'{package_url}/{release}/helm'
            r = requests.delete(url, headers=headers)
            r.raise_for_status()

    def delete(self, namespace, package):
        """Delete a package from a namespace.

        Args:
            namespace: Namespace.
            package: Package in the namespace.

        Returns: None

        Raises: HTTPError if deleting the package failed.
        """
        url = f'{self._quay_api}/repository/{namespace}/{package}'
        r = requests.delete(url, headers=self._oauth_header)
        r.raise_for_status()


class Koji:
    """Koji.

    Collects methods to work with Koji.

    Attributes:
        _kojihub: URL to Koji Hub for API access, excluding trailing /.
            Example: https://koji.fedoraproject.org/kojihub
        _kojiroot: URL to Koji root, where build artifacts are stored,
            excluding trailing /.
            Example: https://kojipkgs.fedoraproject.org/
        _session: Koji client session talking to the hub.
    """
    def __init__(self, kojihub, kojiroot):
        self._kojihub = kojihub
        self._pathinfo = koji.PathInfo(kojiroot)
        self._session = koji.ClientSession(self._kojihub)

    def download_manifest(self, nvr, tmpdir):
        """Download and unpack the operator manifest archive.

        Args:
            nvr: NVR of the build from where the manifest archive should be
                downloaded.
            tmpdir (PosixPath): Temporary directory where the archive is
                unpacked.

        Returns: None

        Raises: HTTPError, in case the downloading the archive failed.
        """
        build = self._session.getBuild(nvr)
        # TODO(csomh): this is the 'old' way of storing the manifests. Remove it
        # once OMPS drops support for it.
        for log in self._session.getBuildLogs(build):
            if log['name'] == 'operator_manifests.zip':
                file_url = f"{self._pathinfo.topdir}/{log['path']}"
                break
        else:
            btype = "operator-manifests"
            archives = self._session.listArchives(buildID=build["id"], type=btype)
            if archives:
                typedir = self._pathinfo.typedir(build, btype)
                file_url = f"{typedir}/{archives[0]['filename']}"

        r = requests.get(file_url)
        r.raise_for_status()

        archive = tmpdir / 'operator_manifests.zip'
        with open(archive, 'wb') as f:
            f.write(r.content)

        with zipfile.ZipFile(archive) as z:
            z.extractall(tmpdir)

        os.remove(archive)


def concatenated_files(directory):
    """Takes a directory and recursively concatenates all the files in it.

    Files are sorted before concatenation.

    Args:
        directory: path to the directory to be parsed

    Returns:
        String with the content of all the files found, concatenated.
    """
    ret = ''
    files = []
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            files.append(os.path.join(dirpath, filename))
    files.sort()
    for file in files:
        with open(file, 'r') as fp:
            ret += fp.read()
    return ret


def is_yaml_file(path):
    """
    Tell if 'path' ends in .yaml or .yml
    """
    return path.endswith(".yaml") or path.endswith(".yml")
