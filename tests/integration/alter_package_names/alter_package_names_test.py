#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import os
import shutil
import pytest
import yaml
import requests
from tests.integration.utils import test_env, make_bundle, is_yaml_file


def has(suffix, manifest_path):
    """
    Tell if 'suffix' can be found in YAML files under 'manifest_path'.

    Args:
        suffix: Suffix string that is looked for.
        manifest_path: Path of the manifest.

    Returns:
        True, if 'suffix' was found, False otherwise.
    """
    for filename in filter(is_yaml_file, os.listdir(manifest_path)):
        path = os.path.join(manifest_path, filename)
        with open(path, "r") as fp:
            if suffix in fp.read():
                return True
    return False


@pytest.mark.skipif(
    not test_env.get("alter_package_name"),
    reason="No configuration to test altering package names",
)
def test_alter_package_name_during_nvr_push(suffix_omps, suffix_quay, koji, tmp_path):
    """
    When the manifest data is pushed to Quay using the NVR endpoint,
    and there is a configuration to alter package names for the namespace,
    then the package name is altered according to this configuration.
    """
    config = test_env["alter_package_name"]
    version = "1.0.0"
    nvr = test_env["koji_builds"]["alter_package_name"]
    suffix_quay.delete(config["namespace"], config["package"] + config["suffix"])

    # check that packageName in the manifest is without the suffix
    koji.download_manifest(nvr, tmp_path)

    assert not has(
        config["suffix"], tmp_path
    ), f"Found {config['suffix']} in the manifest of '{nvr}'"

    response = suffix_omps.fetch_nvr(
        organization=config["namespace"], repo=config["package"], nvr=nvr
    )
    response.raise_for_status()

    quay_bundle = yaml.safe_load(
        make_bundle(
            suffix_quay.get_bundle(
                config["namespace"], config["package"] + config["suffix"], version,
            )
        )
    )

    assert quay_bundle["packageName"] == config["package"] + config["suffix"]


@pytest.mark.skipif(
    not test_env.get("alter_package_name"),
    reason="No configuration to test altering package names",
)
def test_alter_package_name_during_archive_push(suffix_omps, suffix_quay, tmp_path):
    """
    When uploading an archive to a repository,
    and there is a configuration to alter package names for the namespace,
    then the package name is altered according to this configuration.
    """

    config = test_env["alter_package_name"]
    manifest_path = "tests/integration/artifacts/nested/"
    version = "1.0.0"
    suffix_quay.delete(config["namespace"], config["package"] + config["suffix"])

    assert not has(
        config["suffix"], manifest_path
    ), f"Found {config['suffix']} in the manifest at '{manifest_path}'"

    archive = shutil.make_archive(tmp_path / "archive", "zip", manifest_path)

    response = suffix_omps.upload(
        organization=config["namespace"], repo=config["package"], archive=archive,
    )

    assert response.status_code == requests.codes.ok

    quay_bundle = yaml.safe_load(
        make_bundle(
            suffix_quay.get_bundle(
                config["namespace"], config["package"] + config["suffix"], version,
            )
        )
    )

    assert quay_bundle["packageName"] == config["package"] + config["suffix"]
