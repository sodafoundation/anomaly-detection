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
from werkzeug.wrappers.request import Request
from anomaly_detection.context import RequestContext

NO_AUTH_ADMIN_TENANT_ID = 'admin_tenant'


class NoAuthMiddleWare(object):
    def __init__(self, app):
        self._app = app

    def __call__(self, environ, start_response):
        req = Request(environ)
        # FIXME: Any other good idea for this.
        if req.path in ['/', '/v1beta', '/v1beta/']:
            return self._app(environ, start_response)

        if 'X-Auth-Token' not in req.headers:
            headers = [('Content-Type', 'text/plain')]
            start_response('400 Bad Request', headers)
            return [b'X-Auth-Token not found in header']

        token = req.headers['X-Auth-Token']
        user_id, _sep, project_id = token.partition(':')
        project_id = project_id or user_id
        remote_address = getattr(req, 'remote_address', '127.0.0.1')
        environ["anomaly_detection.context"] = RequestContext(user_id,
                                                              project_id,
                                                              is_admin=True,
                                                              remote_address=remote_address)
        return self._app(environ, start_response)

