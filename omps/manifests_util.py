#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

"""Helper classes/functions for operator manifests"""

import logging
import io

import yaml

from operatorcourier.api import build_and_verify
from omps.errors import QuayCourierError

logger = logging.getLogger(__name__)


class ManifestBundle:
    """Provides metadata of operator bundle"""

    @classmethod
    def from_dir(cls, source_dir_path):
        """Build bundle from specified directory

        :param source_dir_path: path to directory with operator manifest
        :rtype: ManifestBundle
        :return: object
        """
        try:
            bundle = build_and_verify(source_dir_path)
        except Exception as e:
            msg = "Operator courier failed: {}".format(e)
            raise QuayCourierError(msg)
        return cls(bundle)

    def __init__(self, bundle):
        """
        :param bundle: bundle built by operator-courier
        """
        self._bundle = bundle

    @property
    def bundle(self):
        """Returns operator bundle"""
        return self._bundle

    @property
    def package_name(self):
        """Returns defined package name from operator bundle"""
        #  op. courier do verification, this should be never empty
        pkgs_yaml = self.bundle['data']['packages']
        pkgs = yaml.safe_load(io.StringIO(pkgs_yaml))
        return pkgs[0]['packageName']
