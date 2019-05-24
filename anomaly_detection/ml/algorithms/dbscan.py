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
from sklearn.preprocessing import StandardScaler
from anomaly_detection.utils import np_json

from anomaly_detection import log
from anomaly_detection.ml import contants
from anomaly_detection.ml.algorithm import AlgorithmBase
from anomaly_detection.utils import config as cfg

LOG = log.getLogger(__name__)

CONF = cfg.CONF


class DBSCAN(AlgorithmBase):
    def __init__(self):
        super(DBSCAN, self).__init__(algorithm_name=contants.GAUSSIAN_MODEL)

    def _select_parameter(self, dataset, labels_true):
        best_ar = 0
        best_ep = 10
        best_ms = 5
        epsilons = np.arange(1, 4, 0.1)
        for epsilon in np.nditer(epsilons):
            for min_samples in range(5, 20, 1):
                db = cluster.DBSCAN(eps=epsilon, min_samples=min_samples).fit(dataset)
                ar = metrics.adjusted_rand_score(labels_true, db.labels_)
                if ar > best_ar:
                    best_ar = ar
                    best_ep = epsilon
                    best_ms = min_samples
        return best_ar, best_ep, best_ms

    def _get_training_data(self):
        num = CONF.training.dataset_number
        data = self.dataset.get(offset=0, limit=num)
        return data[:, 0:2], data[:, 2]

    def _get_test_data(self):
        num = CONF.training.dataset_number
        data = self.dataset.get(limit=num//2)
        return data[:, 0:2]

    def create_training(self, training):
        data, labels_true = self._get_training_data()
        st_data = StandardScaler().fit_transform(data)
        # The epsilon and min_samples value with highest adjusted-rand-score will be selected as threshold
        ar_score, eps, min_samples = self._select_parameter(st_data, labels_true)
        model_data = {"adjusted_rand_score": ar_score, "epsilon": eps, "min_samples": min_samples}
        LOG.info("parameters: %s", model_data)
        return np_json.dumps(model_data)

    def get_training_figure(self, training):
        test_data = self._get_test_data()
        md = np_json.loads(training.model_data)
        eps = md["epsilon"]
        min_samples = md["min_samples"]
        adjusted_rand_score = md["adjusted_rand_score"]
        st_test_data = StandardScaler().fit_transform(test_data)
        db = cluster.DBSCAN(eps=eps, min_samples=min_samples).fit(st_test_data)
        core_samples_mask = np.zeros_like(db.labels_, dtype=bool)
        core_samples_mask[db.core_sample_indices_] = True
        labels = db.labels_
        LOG.debug("eps: %s, minPts: %s adjusted_rand_score: %s", eps, min_samples, adjusted_rand_score)
        fig = plt.figure()
        plt.title('DBSCAN Estimated Figure')
        plt.xlabel("IOPS (tps)")
        plt.ylabel("Latency (μs)")

        # Black removed and is used for noise instead.
        if CONF.dbscan_figure_style == "core_border_spectral":
            unique_labels = set(labels)
            colors = [plt.cm.Spectral(each)
                      for each in np.linspace(0, 1, len(unique_labels))]
            for k, col in zip(unique_labels, colors):
                class_member_mask = (labels == k)

                if k == -1:
                    # Black used for noise.
                    col = [0, 0, 0, 1]
                    xy = test_data[class_member_mask & ~core_samples_mask]
                    plt.plot(xy[:, 0], xy[:, 1], 'o', markerfacecolor=tuple(col),
                             markeredgecolor='k', markersize=6, label='noise point')
                    continue
                xy = test_data[class_member_mask & core_samples_mask]
                plt.plot(xy[:, 0], xy[:, 1], 'o', markerfacecolor=tuple(col),
                         markeredgecolor='k', markersize=14, label='core point')
                xy = test_data[class_member_mask & ~core_samples_mask]
                plt.plot(xy[:, 0], xy[:, 1], 'o', markerfacecolor=tuple(col),
                         markeredgecolor='k', markersize=6, label='border point')
        else:
            xy = test_data[(labels == 0)]
            plt.plot(xy[:, 0], xy[:, 1], 'bx', label='normal  point')
            xy = test_data[(labels == -1)]
            plt.plot(xy[:, 0], xy[:, 1], 'ro', label='outlier point')
            plt.legend(loc='upper right')
        return fig

    def prediction(self, training, dataset):
        pass

    def get_prediction_figure(self, training, dataset):
        pass
