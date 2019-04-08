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
    organizations = {
        "public-org": {
            "public": True,
            "oauth_token" "application_access_token_goes_here"
        }
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

* please install `rpm-devel` (Fedora) or `rpm` (Ubuntu) package to be able
build `koji` dependency `rpm-py-installer` in `tox`:
```bash
sudo dnf install -y rpm-devel
```
* run:
```bash
tox
```



To run tests manually, you can use pytest directly:
```bash
py.test tests/
```
