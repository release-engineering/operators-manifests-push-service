#
# Copyright (C) 2019 Red Hat, Inc
# see the LICENSE file for license
#

from flask import Flask

from .push import BLUEPRINT as PUSH_BP


app = Flask('omps')

app.register_blueprint(PUSH_BP, url_prefix='/push')
