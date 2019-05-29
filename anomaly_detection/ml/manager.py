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
import io

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

from anomaly_detection.db.base import Base
from anomaly_detection.utils import import_object
from anomaly_detection.utils import config as cfg

CONF = cfg.CONF

training_opts = [
    cfg.StrOpt('dataset_source_type',
               choices=['csv', 'database'],
               default='csv',
               help='Training dataset source type'),
    cfg.StrOpt('dataset_csv_file_name',
               default='performance.csv',
               help='Training dataset csv file name'),
    cfg.IntOpt('dataset_number',
               default=10000,
               help='Dataset number which is used to training')
]

CONF.register_opts(training_opts, "training")


def print_figure(fig, fmt='png'):
    output = io.BytesIO()

    if fmt not in ['png', 'jpg', 'jpeg', 'raw', 'tif', 'tiff', 'rgba']:
        raise TypeError('unsupported image type: %s' % fmt)
    canvas = FigureCanvas(fig)
    getattr(canvas, 'print_' + fmt)(output)
    return output.getvalue()


class MLManager(Base):
    _ALGORITHM_MAPPING = {"gaussian": "anomaly_detection.ml.algorithms.gaussian.Gaussian",
                          "dbscan": "anomaly_detection.ml.algorithms.dbscan.DBSCAN"}

    def __init__(self):
        super(MLManager, self).__init__()

    def _get_algorithm(self, name='gaussian'):
        return import_object(self._ALGORITHM_MAPPING[name.lower()])

    def create_training(self, ctx, training):
        algorithm = training.get("algorithm")
        driver = self._get_algorithm(algorithm)
        training["model_data"] = driver.create_training(training)
        return self.db.training_create(ctx, training)

    def get_training_figure(self, ctx, training_id, fmt):
        training = self.db.training_get(ctx, training_id)
        algorithm = training.get("algorithm")
        driver = self._get_algorithm(algorithm)
        fig = driver.get_training_figure(training)
        return print_figure(fig, fmt)

    def prediction(self, ctx, training_id, dataset):
        training = self.db.training_get(ctx, training_id)
        algorithm = training.get("algorithm")
        driver = self._get_algorithm(algorithm)
        return driver.prediction(training, dataset)

    def get_prediction_figure(self, ctx, training_id, dataset, fmt):
        training = self.db.training_get(ctx, training_id)
        algorithm = training.get("algorithm")
        driver = self._get_algorithm(algorithm)
        fig = driver.get_prediction_figure(training, dataset)
        return print_figure(fig)

