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

from anomaly_detection import log
from anomaly_detection.utils import config as cfg

CONF = cfg.CONF
log.register_opts(CONF)

api_opts = [
    cfg.StrOpt('listen_ip',
               default='0.0.0.0',
               help='API server listen ip'),
    cfg.StrOpt('listen_port',
               default='8085',
               help='API server listen ip')

    ]
CONF.register_opts(api_opts, "apiserver")

training_opts = [
    cfg.StrOpt('dataset_source_type',
               choices=['csv', 'database'],
               default='csv',
               help='Training dataset source type'),
    cfg.StrOpt('dataset_csv_file_name',
               default='performance.csv',
               help='Training dataset csv file name')
]

CONF.register_opts(training_opts, "training")
