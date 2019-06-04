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
from anomaly_detection.data_generator.client import TelemetryClient
from anomaly_detection.utils import config as cfg

LOG = log.getLogger(__name__)
CONF = cfg.CONF

data_parser_opts = [
    cfg.StrOpt('cron_expression',
               default='*/10 * * * * *',
               help='Cron expression')
]

CONF.register_opts(data_parser_opts, "data_generator")


class Job(object):
    def __init__(self, name, retries=3):
        self._name = name
        self._retries = retries

    def run(self, *args, **kwargs):
        raise NotImplemented

    def __call__(self, *args, **kwargs):
        retries = self._retries
        for index in range(1, retries + 1):
            try:
                self.run(*args, **kwargs)
            except Exception as e:
                if index > retries:
                    LOG.error('%s\nall retry failed, exit.', e)
                    raise
                else:
                    LOG.error("%s ,retry %d time(s)", e, index)
            else:
                break


class CollectMetricsJob(Job):
    def __init__(self):
        super(CollectMetricsJob, self).__init__("collect_metrics")
        self._client = TelemetryClient()
        self.expression = CONF.data_generator.cron_expression

    def run(self, *args, **kwargs):
        self._client.collect_metrics()
