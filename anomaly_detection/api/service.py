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

from flask import Blueprint
from flask import jsonify
from flask import request
from flask import Response

from anomaly_detection import log
from anomaly_detection.ml import manager
from anomaly_detection.api.view import training as training_view

service = Blueprint("service", __name__)
LOG = log.getLogger(__name__)
ml_mgr = manager.MLManager()

training_view_builder = training_view.ViewBuilder()


# List Algorithms
# URL: GET /v1beta/<tenant_id>/algorithms
@service.route("<tenant_id>/algorithm", methods=['GET'])
def list_algorithm(tenant_id):
    resp = {
        'algorithms': [
            {
                'name': 'gaussian',
                'description': 'gaussian distribution'
            }
        ]

    }
    return jsonify(resp), 200


# Create Training
# URL: POST /v1beta/<tenant_id>/training
# Request Body:
# {
#     'training': {
#         'name': 'training001',
#         'description': 'training testing',
#         'algorithm': 'gaussian',
#         'properties': {
#             'key1': 1,
#             'key2': '2'
#         }
#     }
# }
@service.route("<tenant_id>/training", methods=['POST'])
def create_training(tenant_id):
    LOG.debug("starting training, tenant_id: %s", tenant_id)
    ctx = request.environ['anomaly_detection.context']
    body = request.get_json().get('training', {})
    body['tenant_id'] = tenant_id
    print(body)
    training = ml_mgr.create_training(ctx, body)
    return jsonify(training_view_builder.detail(training)), 200


@service.route("<tenant_id>/training/<training_id>/pic.png", methods=['GET'])
def get_training_pic(tenant_id, training_id):
    LOG.debug("get training pic, tenant_id: %s", tenant_id)
    ctx = request.environ['anomaly_detection.context']
    img = ml_mgr.get_training_pic(ctx, training_id)
    return Response(img, mimetype='image/png')


