#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import requests


class OMPS(object):
    """OMPS service.

    Collects methods to work with the OMPS service.

    Attributes:
        _api_url: URL of the OMPS API. Including version, excluding trailing /.
        _organization: Organization configured in OMPS.
            This is the namespace to be used in the Quay App Registry.
    """
    def __init__(self, api_url, organization, quay_token):
        self._api_url = api_url
        self._organization = organization
        self._auth = {'Authorization': quay_token}

    @property
    def organization(self):
        """Organization configured in OMPS."""
        return self._organization

    def upload(self, repo, archive, organization=None, version=None,
               field='file'):
        """Create a new release for a package by uploading an archive.

        Args:
            repo: Repository where the new release is uploaded.
            archive: Path of the archive to upload.
            organization: Name of the organization where the repo belongs.
                If None, the organization configured in OMPS is used.
            version: Version to be used for this release.
                If None, OMPS will create it.

        Returns:
            A requests.Response object.
            http://docs.python-requests.org/en/master/api/#requests.Response

        Raises: None.
        """
        url = '{api}/{org}/{repo}/zipfile{version}'.format(
            api=self._api_url,
            org=organization or self._organization,
            repo=repo,
            version='' if not version else '/' + version)
        files = {field: open(archive, 'rb')}

        return requests.post(url, files=files, headers=self._auth)

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
        url = '{api}/{org}/{repo}{version}'.format(
            api=self._api_url,
            org=organization,
            repo=repo,
            version='' if not version else '/' + version)

        return requests.delete(url, headers=self._auth)


class QuayAppRegistry(object):
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
    def __init__(self, api_url):
        self._api_url = api_url
        self._token = None

    def login(self, username, password):
        """Login to Quay and store token.

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
        url = '{api}/users/login'.format(api=self._api_url)

        r = requests.post(url, json=data)
        r.raise_for_status()

        self._token = r.json()['token']

    @property
    def token(self):
        return self._token

    def get_releases(self, namespace, package):
        """Get all releases for a package.

        Args:
            namespace: Namespace.
            package: Package.

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
        url = '{api}/packages/{namespace}/{package}'.format(
            api=self._api_url,
            namespace=namespace,
            package=package)
        headers = {'Authorization': self._token}

        r = requests.get(url, headers=headers)
        if r.status_code == requests.codes.not_found:
            return []
        else:
            r.raise_for_status()

        return r.json()

    def get_release(self, namespace, package, release):
        for rel in self.get_releases(namespace, package):
            if rel['release'] == release:
                return rel
        return {}

    def get_packages(self, namespace):
        """Get all packages from a namespace.

        Args:
            namespace: Namespace.

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
        url = '{api}/packages'.format(api=self._api_url)
        headers = {'Authorization': self._token}
        payload = {'namespace': namespace}

        r = requests.get(url, headers=headers, params=payload)
        r.raise_for_status()

        return r.json()

    def delete_releases(self, name, releases):
        """Delete a list of releases from a package.

        Args:
            name: 'namespace/package' to delete releases from.
            releases: List of releases to delete.

        Returns:
            None

        Raises:
            HTTPError: Deleting a release failed.
        """
        package_url = '{api}/packages/{name}'.format(
            api=self._api_url,
            name=name)
        headers = {'Authorization': self._token}

        for release in releases:
            url = '{package_url}/{release}/helm'.format(
                package_url=package_url,
                release=release)
            r = requests.delete(url, headers=headers)
            r.raise_for_status()

    def clean_up(self, namespace, package_prefix):
        """Clean up some packages.

        Used to remove content from packages used for integration testing.

        Args:
            namespace: Namespace.
            package_prefix: Packages in the namespace starting with this string
                will be cleaned up.

        Returns:
            None

        Raises:
            None.
        """
        for package in self.get_packages(namespace):
            name_prefix = '{namespace}/{package_prefix}'.format(
                namespace=namespace,
                package_prefix=package_prefix)
            if package['name'].startswith(name_prefix):
                self.delete_releases(package['name'], package['releases'])
