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
from anomaly_detection.db.base import Base
from anomaly_detection.utils import import_object


class MLManager(Base):
    _ALGORITHM_MAPPING = {"gaussian": "anomaly_detection.ml.algorithms.gaussian.Gaussian"}

    def __init__(self):
        super(MLManager, self).__init__()

    def _get_algorithm(self, name):
        return import_object(self._ALGORITHM_MAPPING[name])

    def create_training(self, ctx, training):
        algorithm = training.get("algorithm")
        driver = self._get_algorithm(algorithm)
        model_data = driver.create_training(training)
        training["model_data"] = model_data
        return self.db.training_create(ctx, training)

    def get_training_pic(self, ctx, training_id):
        training = self.db.training_get(ctx, training_id)
        algorithm = training.get("algorithm")
        driver = self._get_algorithm(algorithm)
        return driver.get_prediction_pic(training)

    def prediction(self, ctx, training_id, dataset):
        training = self.db.training_get(ctx, training_id)
        algorithm = training.get("algorithm")
        driver = self._get_algorithm(algorithm)
        return driver.prediction(training, dataset)

    def get_prediction_pic(self, ctx, training_id, dataset):
        training = self.db.training_get(ctx, training_id)
        algorithm = training.get("algorithm")
        driver = self._get_algorithm(algorithm)
        return driver.get_prediction_pic(training, dataset)

