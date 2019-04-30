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

from anomaly_detection import log
from anomaly_detection.ml import manager

service = Blueprint("service", __name__)
LOG = log.getLogger(__name__)
ml_mgr = manager.MLManager()
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
    body = request.get_json()
    training = body['training']
    training['tenant_id'] = tenant_id
    print(training)
    resp = ml_mgr.create_training(ctx, training)
    return jsonify(resp), 200


