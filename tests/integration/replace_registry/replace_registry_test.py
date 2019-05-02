#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import os
import shutil
import pytest
from distutils import dir_util
from itertools import cycle
from tests.integration.utils import test_env, Bundle


def is_yaml_file(path):
    """
    Tell if 'path' ends in .yaml or .yml
    """
    return path.endswith(".yaml") or path.endswith(".yml")


@pytest.mark.skipif(
    not test_env.get("replace_registry"),
    reason="No configuration to replace registries.",
)
def test_replace_during_nvr_push(omps, quay, koji, tmp_path):
    """
    When the manifest data of an operator image has a nested structure,
    and the manifest data is pushed to Quay using the NVR endpoint,
    and there is a configuration to replace registries,
    then the bundle in Quay has the registries replaces accordingly.
    """
    version = "1.0.0"
    nvr = test_env["koji_builds"]["replace_registry"]
    quay.delete(test_env["test_namespace"], test_env["test_package"])

    koji.download_manifest(nvr, tmp_path)

    def koji_registries(replace_conf, path):
        """
        Find which 'old' registries from 'replace_conf' can be found in
        the manifest at 'path'

        Args:
            replace_conf: List of {'old': ..., 'new': ...} dictionaries.
            path: Path of the manifest.

        Returns:
            List of registries (strings) which were found in the manifest at 'path'.
        """
        content = ""
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filter(is_yaml_file, filenames):
                path = os.path.join(dirpath, filename)
                with open(path, "r") as fp:
                    content += fp.read()

        found = []
        for conf in replace_conf:
            if conf["old"] in content:
                found.append(conf)

        return found

    registries_to_replace = koji_registries(test_env["replace_registry"], tmp_path)
    assert registries_to_replace, (
        f"The 'replace_registry' test configuration should have at least one of the "
        f"'old' registries present in the manifest of '{nvr}'"
    )

    response = omps.fetch_nvr(
        organization=test_env["test_namespace"], repo=test_env["test_package"], nvr=nvr
    )
    response.raise_for_status()

    quay_bundle = Bundle(
        quay.get_bundle(
            test_env["test_namespace"],
            test_env["test_package"],
            version,
            authorization=None,
        )
    )

    for config in registries_to_replace:
        assert config["old"] not in quay_bundle
        assert config["new"] in quay_bundle


@pytest.mark.skipif(
    not test_env.get("replace_registry"),
    reason="No configuration to replace registries.",
)
@pytest.mark.parametrize(
    "manifest_path",
    [
        ("tests/integration/artifacts/replace_registry/nested/"),
        ("tests/integration/artifacts/replace_registry/flat/"),
    ],
    ids=["nested", "flat"],
)
def test_replace_during_archive_push(omps, quay, tmp_path_factory, manifest_path):
    """
    When uploading an archive to a repository,
    and there is a configuration to replace registries,
    then the bundle in Quay has the registries replaces accordingly.
    """

    version = "1.0.0"
    # Make sure there test_env['test_package'] operator is empty.
    releases = [
        r["release"]
        for r in quay.get_releases(test_env["test_namespace"], test_env["test_package"])
    ]
    quay.delete_releases(
        "/".join([test_env["test_namespace"], test_env["test_package"]]), releases
    )

    # Use the registries which are expected to be replaced.
    artifacts_dir = tmp_path_factory.mktemp("artifacts")
    dir_util.copy_tree(manifest_path, artifacts_dir.as_posix())
    replace_conf = cycle(test_env["replace_registry"])
    for dirpath, dirnames, filenames in os.walk(artifacts_dir):
        for filename in filter(is_yaml_file, filenames):
            path = os.path.join(dirpath, filename)
            with open(path, "r") as fp:
                content = fp.read()
            content_changed = False

            # In order to make sure that all the elements from the
            # configuration list are used, cycle through the list of
            # configuration while replacing the placeholder.
            #
            # This is also required for the check at the end of the test to
            # work when there are multiple replacements configured.
            while r"{REGISTRY}" in content:
                content = content.replace(r"{REGISTRY}", next(replace_conf)["old"], 1)
                content_changed = True

            if content_changed:
                with open(path, "w") as fp:
                    fp.write(content)

    archive_dir = tmp_path_factory.mktemp("archive")
    archive = shutil.make_archive(archive_dir / "archive", "zip", artifacts_dir)
    response = omps.upload(
        organization=test_env["test_namespace"],
        repo=test_env["test_package"],
        archive=archive,
    )
    response.raise_for_status()

    quay_bundle = Bundle(
        quay.get_bundle(
            test_env["test_namespace"],
            test_env["test_package"],
            version,
            authorization=None,
        )
    )

    for config in test_env["replace_registry"]:
        assert config["old"] not in quay_bundle
        assert config["new"] in quay_bundle
