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


import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import multivariate_normal
from sklearn.metrics import f1_score
import anomaly_detection.ml.dataset as ds



def feature_normalize(dataset):
    mu = np.mean(dataset, axis=0)
    sigma = np.std(dataset, axis=0)
    return (dataset - mu) / sigma


def estimate_gaussian(dataset):
    mu = np.mean(dataset, axis=0)
    sigma = np.cov(dataset.T)
    return mu, sigma


def multivariate_gaussian(dataset, mu, sigma):
    p = multivariate_normal(mean=mu, cov=sigma)
    return p.pdf(dataset)


def select_threshold_by_CV(probs,gt):
    best_epsilon = 0
    best_f1 = 0
    stepsize = (max(probs) - min(probs)) / 1000
    epsilons = np.arange(min(probs), max(probs), stepsize)
    for epsilon in np.nditer(epsilons):
        predictions = (probs < epsilon)
        f = f1_score(gt, predictions, average="binary")
        if f > best_f1:
            best_f1 = f
            best_epsilon = epsilon
    return best_f1, best_epsilon


tr_data = ds.read('../dataset/performance-tr.csv')
cv_data = ds.read('../dataset/performance-cv.csv')
gt_data = ds.read('../dataset/performance-gt.csv')

n_training_samples = tr_data.shape[0]
n_dim = tr_data.shape[1]

plt.figure()
plt.xlabel("Latency (ms)")
plt.ylabel("Throughput (mb/s)")
plt.plot(tr_data[:, 0], tr_data[:, 1], "bx")
plt.show()

mu, sigma = estimate_gaussian(tr_data)
p = multivariate_gaussian(tr_data, mu, sigma)

p_cv = multivariate_gaussian(cv_data, mu, sigma)
fscore, ep = select_threshold_by_CV(p_cv, gt_data)
outliers = np.asarray(np.where(p < ep))

plt.figure()
plt.xlabel("Latency (ms)")
plt.ylabel("Throughput (mb/s)")
plt.plot(tr_data[:, 0], tr_data[:, 1], "bx")
plt.plot(tr_data[outliers, 0], tr_data[outliers, 1], "ro")
plt.show()
