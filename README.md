# Operators Manifests Push Service (OMPS)

[![Build Status](https://travis-ci.org/release-engineering/operators-manifests-push-service.svg?branch=master)](https://travis-ci.org/release-engineering/operators-manifests-push-service)
[![Coverage Status](https://coveralls.io/repos/github/release-engineering/operators-manifests-push-service/badge.svg?branch=master)](https://coveralls.io/github/release-engineering/operators-manifests-push-service?branch=master)

Service for pushing operators manifests to quay.io from various sources.

## Settings

### Configuration file

Setting location of config file:
```
export OMPS_CONF_FILE=/path/to/config.py
export OMPS_CONF_SECTION=ProdConfig
```

Configuration file example:
```
class ProdConfig:
    SECRET_KEY = "123456789secretkeyvalue"
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DEFAULT_RELEASE_VERSION = "1.0.0"  # default operator manifest version

    # configuration of Koji URLs
    KOJIHUB_URL = 'https://koji.fedoraproject.org/kojihub'
    KOJIROOT_URL = 'https://kojipkgs.fedoraproject.org/'

    # Timeout in seconds for Koji and Quay requests
    REQUEST_TIMEOUT = 28

    # Organization access
    ORGANIZATIONS = {
        "public-org": {
            "public": True,
            "oauth_token" "application_access_token_goes_here"
            "replace_registry": [
                {
                    "old": "quay.io",
                    "new": "example.com",
                },
            ]
        }
    }

    # Greenwave integration
    GREENWAVE = {
        "url": "https://greenwave.example.com",
        "context": "omps_push",
        "product_version": "cvp"
    }
```

### Configuration of quay's organizations

#### Auto publishing new repositories

By default OMPS uses auth tokens for quay's CNR endpoint passed by user in HTTP
`Authorization` header (see Authorization section).

However CNR endpoint doesn't provide full access to quay applications.
OMPS needs oauth [access token](https://docs.quay.io/api/) to be able make
repositories public in chosen organizations.

Required permissions:
* Administer Repositories

Organizations configuration options:
* `public`: if `True` OMPS publish all new repositories in that organization
 (requires `oauth_token`). Default is `False` repositories are private.
* `oauth_token`: application oauth access token from quay.io

#### Replacing registries URLs in manifest files

If organization have configured `replace_registry` section in the particular
organization:
```
"replace_registry": [
    {
        "old": "quay.io",
        "new": "example.com",
    },
]
```
All specified `old` registries will be replaced by `new` in all manifests yaml
files for that organization.

You can pattern match and replace registry strings with the regexp field instead
of matching whole strings.  Both `old` and `new` will be evalutated as regexes
when `regexp` is set to `True`.  If `regexp` is missing it defaults to `False`.
Here's an example:
```
"replace_registry": [
    {
        "old": "quay.io$",
        "new": "example.com",
        "regexp": True,
    },
]
```
Replacements occur when pushing manifests into the application registry.

#### Altering repository names

Organizations can be configured so a suffix is appended to the repository name.
The suffix is only applied if the repository name does not already end with the suffix.
Example configuration:
```
"repository_suffix": "-suffix"
```

### Greenwave integration

This is optional. When `GREENWAVE` settings are missing in config file checks
are skipped.

[Greenwave](https://pagure.io/greenwave) integration allows OMPS to check if
koji builds meets policies defined in Greenwave before operators from koji
builds are pushed to quay.
(Note: this check is skipped for pushing from zipfiles directly)


## Running service

The best way is to run service from a container:
```bash
docker build -t omps:latest .
docker run --rm -p 8080:8080 omps:latest
```

Running container with custom CA certificate
```bash
docker run --rm -p 8080:8080 -e CA_URL='http://example.com/ca-cert.crt' omps:latest
```

Running container with customized number of workers (default: 8):
```bash
docker run --rm -p 8080:8080 -e WORKERS_NUM=6 omps:latest
```

Running container with custom worker timeout (default: 30 seconds):
```bash
docker run --rm -p 8080:8080 -e WORKER_TIMEOUT=60 omps:latest
```


## Usage

### Authorization

Users are expected to use quay.io token that can be acquired by the following
command:

```bash
TOKEN=$(curl -sH "Content-Type: application/json" -XPOST https://quay.io/cnr/api/v1/users/login -d '
{
    "user": {
        "username": "'"${QUAY_USERNAME}"'",
        "password": "'"${QUAY_PASSWORD}"'"
    }
}' | jq -r '.token')
```

Quay token must be passed to OMPS app via HTTP `Authorization` header

```bash
curl -H "Authorization: ${TOKEN}" ...
```

Is recommended to use [robot accounts](https://docs.quay.io/glossary/robot-accounts.html).


### REST API

* [REST API Version 2](docs/usage/v2.md)
* **Deprecated** [REST API Version 1](docs/usage/v1.md)


## Development

### Running Flask dev. server

To run app locally for testing, use:
```bash
OMPS_DEVELOPER_ENV=true FLASK_APP=omps/app.py flask run
```

### Installing with test dependencies

To install test dependencies from local directory use following:
```bash
pip install '.[test]'
```


### Running tests

Project is integrated with tox:

* please install `rpm-devel` and `krb5-devel`  (Fedora) or `rpm` and
  `libkrb5-dev` (Ubuntu) package to be able build `koji` dependency
  `rpm-py-installer` in `tox`:

```bash
sudo dnf install -y rpm-devel krb5-devel
```
* run:
```bash
tox
```

Additionally, you can run the following to execute tests against the
latest *unreleased* version of Operator Courier:

```bash
tox -e 'py{36,37}-courier_master'
```

To run tests manually, you can use pytest directly:
```bash
py.test tests/
```
