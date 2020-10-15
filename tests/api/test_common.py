#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import os

from omps.constants import YAML_WIDTH
from omps.api.common import (
    _yield_yaml_files,
    adjust_csv_annotations,
    get_yaml_parser,
    replace_registries,
)
from omps.quay import QuayOrganization


def test_replace_registries(datadir):
    """Test if registry is replaced in all files"""
    dir_path = os.path.join(datadir, 'etcd_op_nested')
    old = 'quay.io'
    new = 'example.com'
    qo = QuayOrganization('testorg', 'random token', replace_registry_conf=[
        {'old': old, 'new': new, 'regexp': False}
    ])

    should_be_replaced = set()
    for fpath in _yield_yaml_files(dir_path):
        with open(fpath, 'r') as f:
            text = f.read()
            if old in text:
                should_be_replaced.add(fpath)

    replace_registries(qo, dir_path)

    for fpath in should_be_replaced:
        with open(fpath, 'r') as f:
            text = f.read()
            assert new in text
            assert old not in text


def test_adjust_csv_annotations(datadir):
    """Test if annotations are applied in ClusterServiceVersion"""
    dir_path = os.path.join(datadir, 'etcd_op_nested')
    csv_annotations = [
        {'name': 'simple', 'value': 'simple-value'},
        {'name': 'complex', 'value': 'value-{package_name}'},
    ]
    expected_annotations = {
        'simple': 'simple-value',
        'complex': 'value-etcd',
    }
    quay_org = QuayOrganization(
        'testorg', 'random token', csv_annotations=csv_annotations)

    should_have_annotations = set()
    for fpath in _yield_yaml_files(dir_path):
        with open(fpath, 'r') as f:
            text = f.read()
            if 'ClusterServiceVersion' in text:
                should_have_annotations.add(fpath)

    assert should_have_annotations, 'Insufficient test data'

    adjust_csv_annotations(quay_org, dir_path, {'package_name': 'etcd'})

    yaml = get_yaml_parser()
    for fpath in should_have_annotations:
        with open(fpath, 'r') as f:
            contents = yaml.load(f.read())
            for name, value in expected_annotations.items():
                assert contents['metadata']['annotations'][name] == value


def test_get_yaml_parser():
    """Test if yaml parser is configured correctly"""
    yaml = get_yaml_parser()
    assert yaml.width == YAML_WIDTH
