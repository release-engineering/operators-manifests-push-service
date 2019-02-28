# Integration Tests for OMPS

This directory stores integration tests for OMPS, one sub-directory for each
feature.

Fixtures can be found in `conftest.py`. Utility functions and classes in
`utils.py`.


## Configuration

Configuring the OMPS and Quay instances used by the tests can be done using
a bunch of `OMPS_INT_TEST_*` prefixed environment variables.

`OMPS_INT_TEST_OMPS_URL`: URL of the OMPS API to be tested.
For example: `https://omps.example.com/v1`.

`OMPS_INT_TEST_OMPS_ORG`: Organization configured in the OMPS instance tested.
For example: 'community-operators'.

`OMPS_INT_TEST_QUAY_URL`: URL of the QUAY API to be used during testing.
For example: `https://quay.io/api/v1`.

`OMPS_INT_TEST_QUAY_USER`: User to authenticate with Quay.

`OMPS_INT_TEST_QUAY_PASSWD`: Password to authenticate with Quay.

All the variables above could be set using [direnv](https://direnv.net/), when
one navigates to the OMPS repo. See `.envrc.example` for a starting point.


## Running the tests

Tests can be triggered from the OMPS repo root with:

```bash
tox -e integration
```

Note, that the `integration` environment is not part of the default `tox`
envlist.

`REQUESTS_CA_BUNDLE` is set in `tox.ini` for the `integration` environment in
order to make custom certificates available in the virtual environment
created. One might want to tweak or delete this value, depending on the OMPS
instance being tested.
