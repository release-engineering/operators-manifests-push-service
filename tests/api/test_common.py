#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import os

from omps.api.common import replace_registries, _yield_yaml_files
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
