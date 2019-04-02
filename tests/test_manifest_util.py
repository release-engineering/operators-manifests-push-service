#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import tempfile

import pytest

from omps.errors import PackageValidationError
from omps.manifests_util import ManifestBundle


class TestManifestBundle:
    """Tests of ManifestBundle class"""

    def test_invalid_bundle(self):
        """Test if proper exception is raised when source data are invalid.
        Uses empty dir to force operator-courier to raise an exception
        """
        with pytest.raises(PackageValidationError) as exc_info, \
                tempfile.TemporaryDirectory() as tmpdir:
            ManifestBundle.from_dir(tmpdir)

        assert str(exc_info.value).startswith('Operator courier failed: ')

    def test_package_name(self, valid_manifest_flatten_dir):
        """Test of property which provides package name"""
        mb = ManifestBundle.from_dir(valid_manifest_flatten_dir.path)
        assert mb.package_name == valid_manifest_flatten_dir.pkg_name
