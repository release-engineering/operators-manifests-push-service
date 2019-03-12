# Integration Tests for OMPS

This directory stores integration tests for OMPS, one sub-directory for each
feature.

Fixtures can be found in `conftest.py`. Utility functions and classes in
`utils.py`.


## Configuration

The integration tests should be configured by a `test.env.yaml` file placed in
the repo.

See [`example.text.env.yaml`](../../example.test.env.yaml) for the list of configuration options and
examples.


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
