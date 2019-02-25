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
```

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

## Usage

### Uploading operators manifests from zipfile

Operator manifests files must be added to zip archive

#### Endpoints

* [POST] `/push/<organization>/<repository>/zipfile/<version>`
* [POST] `/push/<organization>/<repository>/zipfile`

Zip file must be attached as `content_type='multipart/form-data'` assigned to
field `file`. See `curl` examples bellow.

If `<version>` is omitted:
* the latest release version will be incremented and used (for example from `2.5.1` to `3.0.0`)
* for new repository a default initial version will be used (`DEFAULT_RELEASE_VERSION` config option)

`<version>` must be unique for repository. Quay doesn't support overwriting of releases.

#### Replies

**OK**

HTTP code: 200

```json
{
  "organization": "organization name",
  "repo": "repository name",
  "version": "0.0.1",
  "extracted_files": ["packages.yml", "..."]
}

```

**Failures**

Error messages have following format:
```
{
  "status": <http numeric code>,
  "error": "<error ID string>",
  "message": "<detailed error description>",
}
```


| HTTP Code / `status` |  `error`    |  Explanation        |
|-----------|------------------------|---------------------|
|400| OMPSUploadedFileError | Uploaded file didn't meet expectations (not a zip file, too big after unzip, corrupted zip file) |
|400| OMPSExpectedFileError | Expected file hasn't been attached |
|404| OMPSOrganizationNotFound | Requested organization is not configured on server side |
|500| QuayLoginError | Server cannot login to quay, probably misconfiguration |
|500| QuayCourierError | operator-courier module raised exception during building and pushing manifests to quay|
|500| QuayPackageError | Failed to get information about application packages from quay |

#### Example
```bash
curl -X POST https://example.com/push/myorg/myrepo/zipfile -F "file=@manifests.zip"
```
or with explicit release version
```bash
curl -X POST https://example.com/push/myorg/myrepo/zipfile/1.1.5 -F "file=@manifests.zip"
```


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
```bash
tox
```

To run tests manually, you can use pytest directly:
```bash
py.test tests/
```
