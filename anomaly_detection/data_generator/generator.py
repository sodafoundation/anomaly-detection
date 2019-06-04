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

from apscheduler.schedulers.blocking import BlockingScheduler

from anomaly_detection.data_generator.jobs import CollectMetricsJob


class Generator(object):
    def __init__(self):
        self._scheduler = BlockingScheduler()

    def add_cron_job(self, job):
        values = job.expression.split()
        if len(values) != 6:
            raise ValueError('Wrong number of fields; got {}, expected 6'.format(len(values)))
        self._scheduler.add_job(job, 'cron', second=values[0], minute=values[1], hour=values[2],
                                day=values[3], month=values[4], day_of_week=values[5], timezone=None)

    def load_jobs(self):
        self.add_cron_job(CollectMetricsJob())

    def run(self):
        self._scheduler.start()
