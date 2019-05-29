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

import functools
import time
import json

from anomaly_detection import log
from anomaly_detection.context import get_admin_context
from anomaly_detection.db import base
from anomaly_detection.exception import LoopingCallDone
from anomaly_detection.ml import csv
from anomaly_detection.utils import config as cfg
from kafka import KafkaConsumer

LOG = log.getLogger(__name__)
CONF = cfg.CONF


data_parser_opts = [
    cfg.StrOpt('csv_file_name',
               default='performance.csv',
               help='Data receiver source file name'),
    cfg.StrOpt('kafka_bootstrap_servers',
               default='localhost:9092',
               help='kafka bootstrap server'),
    cfg.StrOpt('kafka_topic',
               default='telemetry_topic',
               help='kafka topic'),
    cfg.IntOpt('kafka_retry_num',
               default=3,
               help='kafka retry num')
]

CONF.register_opts(data_parser_opts, "data_parser")


class LoopingCall(object):
    def __init__(self, interval=60, raise_on_error=False):
        self._interval = interval
        self._raise_on_error = raise_on_error

    def __call__(self, func):
        functools.update_wrapper(self, func)

        def wrapper(*args, **kwargs):
            while True:
                last_run = time.time()
                try:
                    func(*args, **kwargs)
                except LoopingCallDone:
                    break
                except Exception as e:
                    if self._raise_on_error:
                        raise
                    print('Error during %s: %s' % (func.__name__, e))
                idle_for = last_run + self._interval - time.time()
                if idle_for > 0:
                    time.sleep(idle_for)
        return wrapper


class DataReceiver(base.Base):
    def __init__(self, name):
        super(DataReceiver, self).__init__()
        self._name = name

    def run(self):
        raise NotImplemented


class CSVDataReceiver(DataReceiver):
    def __init__(self):
        super(CSVDataReceiver, self).__init__(name="csv")
        self.once = False
        self.csv_file = CONF.data_parser.csv_file_name

    def run(self):
        LOG.info("CSV Data Receiver running ...")
        perf_array = csv.read(self.csv_file)
        LOG.info("Starting to write %s items to database", perf_array.shape[0])
        for perf in perf_array:
            perf_dict = {
                'iops': perf[0],
                'latency': perf[1],
                'ground_truth': perf[2]
            }
            ctx = get_admin_context()
            self.db.performance_create(ctx, perf_dict)
        LOG.info("Writing to database is done")


class KafkaDataReceiver(DataReceiver):
    def __init__(self):
        super(KafkaDataReceiver, self).__init__(name="kafka")

    def consume(self):
        consumer = KafkaConsumer(CONF.data_parser.kafka_topic,
                                 bootstrap_servers=CONF.data_parser.kafka_bootstrap_servers)
        for msg in consumer:
            perf = json.loads(msg.value)
            LOG.info("receive performance data:%s", perf)
            ctx = get_admin_context()
            self.db.performance_create(ctx, perf)

    def run(self):
        retry = CONF.data_parser.kafka_retry_num
        for index in range(1, retry+1):
            try:
                self.consume()
            except KeyboardInterrupt:
                LOG.info("Bye!")
                break
            except Exception as e:
                if index > retry:
                    LOG.error('%s\nall retry failed, exit.', e)
                    raise
                else:
                    LOG.error("%s ,retry %d time(s)", e, index)


class Manager(base.Base):
    def __init__(self, receiver_name):
        super(Manager, self).__init__()
        if receiver_name == 'csv':
            self._receiver = CSVDataReceiver()
        else:
            self._receiver = KafkaDataReceiver()

    def run(self):
        self._receiver.run()
