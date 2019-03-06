#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

import os


TEST_NAMESPACE = os.getenv('OMPS_INT_TEST_OMPS_ORG')
TEST_PACKAGE = os.getenv('OMPS_INT_TEST_PACKAGE', default='int-test')
