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

import json

import matplotlib.pyplot as plt
import numpy as np
from sklearn import cluster
from sklearn import metrics

from anomaly_detection.ml import contants
from anomaly_detection.ml.algorithm import AlgorithmBase


class DBSCAN(AlgorithmBase):
    def __init__(self):
        super(DBSCAN, self).__init__(algorithm_name=contants.GAUSSIAN_MODEL)

    def _select_parameter(self, dataset, labels_true):
        best_ar = 0
        best_ep = 10
        best_ms = 5
        for eps in range(10, 100, 10):
            for min_samples in range(5, 20, 2):
                db = cluster.DBSCAN(eps=eps, min_samples=min_samples).fit(dataset)
                ar = metrics.adjusted_rand_score(labels_true, db.labels_)
                if ar > best_ar:
                    best_ar = ar
                    best_ep = eps
                    best_ms = min_samples
        return best_ar, best_ep, best_ms

    def _get_training_data(self):
        data = self.dataset.get(offset=4999, limit=4999)
        return data[:, 0:2], data[:, 2]

    def _get_test_data(self):
        data = self.dataset.get(limit=4999)
        return data[:, 0:2]

    def create_training(self, training):
        data, labels_true = self._get_training_data()
        # The epsilon and min_samples value with highest adjusted-rand-score will be selected as threshold
        ar_score, eps, min_samples = self._select_parameter(data, labels_true)
        return json.dumps({"adjusted_rand_score": ar_score, "epsilon": eps, "min_samples": min_samples})

    def get_training_figure(self, training):
        test_data = self._get_test_data()
        md = json.loads(training.model_data)
        eps = md["epsilon"]
        min_samples = md["min_samples"]
        db = cluster.DBSCAN(eps=eps, min_samples=min_samples).fit(test_data)
        core_samples_mask = np.zeros_like(db.labels_, dtype=bool)
        core_samples_mask[db.core_sample_indices_] = True
        labels = db.labels_

        fig = plt.figure()
        plt.title('DBSCAN Estimated Figure')
        plt.xlabel("Throughput(IOPS)(IO/s)")
        plt.ylabel("Latency (us)")
        xy = test_data[(labels == 0)]
        plt.plot(xy[:, 0], xy[:, 1], 'bx')
        xy = test_data[(labels == -1)]
        plt.plot(xy[:, 0], xy[:, 1], 'ro')
        return fig

    def prediction(self, training, dataset):
        pass

    def get_prediction_figure(self, training, dataset):
        pass
