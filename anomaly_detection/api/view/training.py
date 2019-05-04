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


class ViewBuilder(object):

    def detail(self, training):
        training_dict = {
            'id': training.get('id'),
            'name': training.get('name'),
            'description': training.get('description'),
            'tenant_id': training.get('tenant_id'),
            'algorithm': training.get('algorithm')
        }

        return {'training': training_dict}
