#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import pytest

from omps.app import app


@pytest.fixture
def client():
    client = app.test_client()

    yield client
