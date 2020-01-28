#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

""" Defines shared functions for API """

import logging
import os

from ruamel.yaml import YAML

from omps.errors import OMPSAuthorizationHeaderRequired


logger = logging.getLogger(__name__)


def extract_auth_token(req):
    """Extracts auth token from request header

    :param req: Flask request
    :rtype: str
    :return: Auth token
    """
    auth_header = req.headers.get('Authorization', None)
    if auth_header is None:
        raise OMPSAuthorizationHeaderRequired(
            "Request contains no 'Authorization' header")

    return auth_header


def replace_registries(quay_org, dir_path):
    """Replace registries URLs in manifests files"""
    if not quay_org.registry_replacing_enabled:
        return

    logger.info("Replacing registries URLs for organization: %s",
                quay_org.organization)

    for filename in _yield_yaml_files(dir_path):
        with open(filename, 'r+') as f:
            text = f.read()
            text = quay_org.replace_registries(text)
            f.seek(0)
            f.write(text)
            f.truncate()
            f.flush()


def adjust_csv_annotations(quay_org, dir_path, context):
    """Annotates ClusterServiceVersion objects based on org config

    Iterate through all the YAML files in search of the
    ClusterServiceVersion objects then set the annotations
    defined in the organization configuration.

    :param quay_org: QuayOrganization
    :param dir_path: str, path to directory with metadata files
    :param context: dict, mapping to dynamic annotation values
    :rtype: None
    """
    if not quay_org.csv_annotations:
        return

    yaml = YAML()
    # for filename in sorted(os.listdir(dir_path)):
    for filename in _yield_yaml_files(dir_path):
        with open(filename, 'r+') as f:
            contents = yaml.load(f.read())
            if contents.get('kind') != 'ClusterServiceVersion':
                continue
            logger.info('Found ClusterServiceVersion in %s', filename)
            csv_annotations = (
                contents.setdefault('metadata', {}).setdefault('annotations', {}))
            for annotation in quay_org.csv_annotations:
                value = annotation['value'].format(**context)
                csv_annotations[annotation['name']] = value

            f.seek(0)
            yaml.dump(contents, f)
            f.truncate()


def _yield_yaml_files(dir_path):
    """Helper function to iterate only through yaml files"""
    for root, _, files in os.walk(dir_path):
        for fname in files:
            fname_lower = fname.lower()
            if fname_lower.endswith('.yml') or fname_lower.endswith('.yaml'):
                yield os.path.join(root, fname)
