#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import tempfile

import pytest

from omps.errors import QuayCourierError
from omps.manifests_util import ManifestBundle


class TestManifestBundle:
    """Tests of ManifestBundle class"""

    def test_invalid_bundle(self):
        """Test if proper exception is raised when source data are invalid.
        Uses empty dir to force operator-courier to raise an exception
        """
        with pytest.raises(QuayCourierError), \
                tempfile.TemporaryDirectory() as tmpdir:
            ManifestBundle.from_dir(tmpdir)

    def test_package_name(self, valid_manifest_dir):
        """Test of property which provides package name"""
        mb = ManifestBundle.from_dir(valid_manifest_dir.path)
        assert mb.package_name == valid_manifest_dir.pkg_name
