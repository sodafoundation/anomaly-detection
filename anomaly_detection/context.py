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


class RequestContext(object):
    def __init__(self, user_id, tenant_id, is_admin=None, is_admin_tenant=None,
                 roles=None, auth_token=None, read_deleted="no", **kwargs):
        self._user_id = user_id
        self.auth_token = auth_token
        self.is_admin = is_admin
        self.is_admin_tenant = is_admin_tenant
        self.roles = roles or []

        self.user_id = user_id
        self.tenant_id = tenant_id

        self.read_deleted = read_deleted

    def to_dict(self):
        values = super(RequestContext, self).to_dict()
        values.update({
            'user_id': getattr(self, 'user_id', None),
            'project_id': getattr(self, 'project_id', None),
            'read_deleted': getattr(self, 'read_deleted', None),
            'remote_address': getattr(self, 'remote_address', None),
            'timestamp': self.timestamp.isoformat() if hasattr(
                self, 'timestamp') else None,
            'quota_class': getattr(self, 'quota_class', None),
            'service_catalog': getattr(self, 'service_catalog', None)})
        return values

    @classmethod
    def from_dict(cls, values):
        return cls(**values)


def get_admin_context():
    return RequestContext(user_id=None,
                          tenant_id=None,
                          is_admin=True)
