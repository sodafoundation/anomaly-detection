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
import numpy as np

from anomaly_detection.context import get_admin_context
from anomaly_detection.db.base import Base
from anomaly_detection.ml import csv
from anomaly_detection.utils import config as cfg

CONF = cfg.CONF


class DataSet(object):
    def get(self, offset=0, limit=1000):
        raise NotImplementedError


class CSVDataSet(DataSet):
    def __init__(self, file_name='performance.csv'):
        self._file_name = file_name

    def get(self, offset=0, limit=10000):
        return csv.read(self._file_name, skip_header=offset, max_rows=offset+limit)


class DBDataSet(DataSet, Base):
    def __init__(self):
        super(DataSet, self).__init__()

    def get(self, offset=0, limit=10000):
        count = self.db.performance_get_count(get_admin_context())
        limit = min(count, limit)
        perfs = self.db.performance_get_all(get_admin_context(), offset=offset, limit=limit)
        data = np.empty(shape=[0, 3])
        for perf in perfs:
            data = np.vstack([data, [perf.iops, perf.latency, perf.ground_truth]])
        return data


class AlgorithmBase(object):

    def __init__(self, *args, **kwargs):
        self.algorithm_name = kwargs.get("algorithm_name")
        source_type = CONF.training.dataset_source_type
        if source_type == 'database':
            self.dataset = DBDataSet()
        else:
            self.dataset = CSVDataSet(CONF.training.dataset_csv_file_name)

    def create_training(self, training):
        raise NotImplementedError

    def get_training_figure(self, training):
        raise NotImplementedError

    def prediction(self, training, dataset):
        raise NotImplementedError

    def get_prediction_figure(self, training, dataset):
        raise NotImplementedError
