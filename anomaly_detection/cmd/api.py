# Copyright 2019 The OpenSDS Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys

from flask import Flask

from anomaly_detection import log
from anomaly_detection.api.middleware.auth import NoAuthMiddleWare
from anomaly_detection.api import v1beta
from anomaly_detection.api.version import version
from anomaly_detection.utils import config as cfg
from anomaly_detection.common import options # load configuration, don't remove

CONF = cfg.CONF

api_opts = [
    cfg.StrOpt('listen_ip',
               default='0.0.0.0',
               help='API server listen ip'),
    cfg.StrOpt('listen_port',
               default='8085',
               help='API server listen ip'),
    cfg.StrOpt('dbscan_figure_style',
               default='blue_red',
               choices=['blue_red', 'core_border_spectral'],
               help='DBSCAN figure output style')

    ]

CONF.register_opts(api_opts, "apiserver")


class ServerManager:
    app = Flask(__name__)

    def __init__(self):
        self._init_server()

    def _init_server(self):
        self.app.url_map.strict_slashes = False
        # add middleware
        self.app.wsgi_app = NoAuthMiddleWare(self.app.wsgi_app)
        # register router
        self.app.register_blueprint(version)
        self.app.register_blueprint(v1beta.service, url_prefix="/v1beta")

    def start(self):
        self.app.run(CONF.apiserver.listen_ip, CONF.apiserver.listen_port)


def main():
    CONF(sys.argv[1:])
    log.setup(CONF, "anomaly_detection")
    server_manager = ServerManager()
    server_manager.start()


if __name__ == '__main__':
    sys.exit(main())
