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

from anomaly_detection import log
from anomaly_detection.data_parser import manager
from anomaly_detection.utils import config as cfg
# need register global_opts
from anomaly_detection.common import options

CONF = cfg.CONF

data_parser_opts = [
    cfg.StrOpt('receiver_name',
               default='csv',
               help='Data receiver name'),
    cfg.StrOpt('csv_file_name',
               default='performance.csv',
               help='Data receiver source file name')
]

CONF.register_opts(data_parser_opts, "data_parser")


def main():
    CONF(sys.argv[1:])
    log.setup(CONF, "anomaly_detection")
    mgr = manager.Manager(CONF.data_parser.receiver_name)
    mgr.run()


if __name__ == '__main__':
    sys.exit(main())
