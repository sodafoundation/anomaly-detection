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

version = Blueprint("version", __name__)
LOG = log.getLogger(__name__)


@version.route("/", methods=['GET'])
@version.route("/v1beta", methods=['GET'])
def get_version():
    LOG.debug("get anomaly detection version")
    return jsonify(name="Anomaly Detection", version="v1beta"), 200

