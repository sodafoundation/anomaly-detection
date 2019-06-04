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

import copy
import json

import requests
from keystoneauth1 import identity
from keystoneauth1 import session as ks

from anomaly_detection import log
from anomaly_detection.utils import config as cfg

LOG = log.getLogger(__name__)
CONF = cfg.CONF

auth_opts = [
    cfg.StrOpt('auth_url',
               default='http://127.0.0.1/identity',
               help='Authentication URL'),
    cfg.StrOpt('auth_type',
               default="password",
               help='Authentication type'),
    cfg.StrOpt('username',
               default="admin",
               help='User name'),
    cfg.StrOpt('password',
               default="opensds@123",
               help='User password'),
    cfg.StrOpt('project_name',
               default='admin',
               help='Project name'),
    cfg.StrOpt('project_domain_name',
               default='Default',
               help='Project domain name'),
    cfg.StrOpt('project_domain_id',
               default='default',
               help='Project domain id'),
    cfg.StrOpt('user_domain_name',
               default="Default",
               help='User domain name'),
    cfg.StrOpt('user_domain_id',
               default="default",
               help='User domain id')
]

generator_opts = [
    cfg.StrOpt('opensds_endpoint',
               default='http://127.0.0.1/:50040',
               help='OpenSDS hotpot endpoint URL'),
    cfg.StrOpt('opensds_backend_driver_type',
               default="lvm",
               help='OpenSDS backend driver type'),
    cfg.StrOpt('api_version',
               default='v1beta',
               help='OpenSDS hotpot api version'),
    cfg.StrOpt('auth_strategy',
               default='keystone',
               help='OpenSDS authentication strategy'),
    cfg.StrOpt('noauth_tenant_id',
               default='e93b4c0934da416eb9c8d120c5d04d96',
               help='NoAuth Tenant ID'),
    cfg.IntOpt('retries',
               default=3,
               help='Failed retries number'),
    cfg.BoolOpt('http_log_debug',
                default=False,
                help='Whether enable the log debug printing'),
    cfg.BoolOpt('insecure',
                default=True,
                help='Using insecure http request'),
    cfg.IntOpt('timeout',
               default=60,
               help='Request timeout in seconds'),
]

CONF.register_opts(auth_opts, "keystone_authtoken")
CONF.register_opts(generator_opts, "data_generator")


class KeystoneClient(object):

    def __init__(self):
        configuration = CONF.keystone_authtoken
        auth = identity.Password(auth_url=configuration.auth_url,
                                 username=configuration.username,
                                 password=configuration.password,
                                 project_name=configuration.project_name,
                                 project_domain_id=configuration.project_domain_id,
                                 project_domain_name=configuration.project_domain_name,
                                 user_domain_id=configuration.user_domain_id,
                                 user_domain_name=configuration.user_domain_name)
        self.session = ks.Session(auth=auth)

    def get_token(self):
        return self.session.get_token()

    def get_tenant_id(self):
        return self.session.get_project_id()


class TelemetryClient(object):
    def __init__(self):
        self.auth_strategy = CONF.data_generator.auth_strategy
        self.default_headers = {
            'User-Agent': "python-anomaly-detection-client",
            'Accept': 'application/json',
        }

        self.tenant_id = CONF.data_generator.noauth_tenant_id
        if self.auth_strategy == "keystone":
            self.keystone_client = KeystoneClient()
            self.tenant_id = self.keystone_client.get_tenant_id()

        self.api_version = CONF.data_generator.api_version
        self.endpoint_url = CONF.data_generator.opensds_endpoint
        pieces = [self.endpoint_url, self.api_version, self.tenant_id]
        self.base_url = '/'.join(s.strip('/') for s in pieces)+"/"

        self.retries = CONF.data_generator.retries
        self.http_log_debug = CONF.data_generator.http_log_debug

        self.request_options = self._set_request_options(
            CONF.data_generator.insecure, CONF.data_generator.timeout)
        self.driver_type = CONF.data_generator.opensds_backend_driver_type

    def _set_request_options(self, insecure, timeout=None):
        options = {'verify': True}
        if insecure:
            options['verify'] = False

        if timeout:
            options['timeout'] = timeout

        return options

    def do_request(self, url, method, **kwargs):
        url = self.base_url+url
        headers = copy.deepcopy(self.default_headers)
        if self.keystone_client is not None:
            headers['X-Auth-Token'] = self.keystone_client.get_token()

        headers.update(kwargs.get('headers', {}))
        options = copy.deepcopy(self.request_options)

        if 'body' in kwargs:
            headers['Content-Type'] = 'application/json'
            options['data'] = json.dumps(kwargs['body'])

        self.log_request(method, url, headers, options.get('data', None))
        resp = requests.request(method, url, headers=headers, **options)
        self.log_response(resp)
        body = None
        if resp.text:
            try:
                body = json.loads(resp.text)
            except ValueError:
                pass
        return resp, body

    def request(self, url, method, **kwargs):
        retries = self.retries
        for index in range(1, retries + 1):
            try:
                self.do_request(url, method, **kwargs)
            except Exception as e:
                if index > retries:
                    LOG.error('%s\nall retry failed, exit.', e)
                    raise
                else:
                    LOG.error("%s ,retry %d time(s)", e, index)
            else:
                break

    def log_request(self, method, url, headers, data=None):
        if not self.http_log_debug:
            return

        string_parts = ['curl -i', ' -X %s' % method, ' %s' % url]

        for element in headers:
            header = ' -H "%s: %s"' % (element, headers[element])
            string_parts.append(header)

        if data:
            string_parts.append(" -d '%s'" % data)
        LOG.info("\nREQ: %s\n", "".join(string_parts))

    def log_response(self, resp):
        if not self.http_log_debug:
            return
        LOG.info(
            "RESP: [%(code)s] %(headers)s\nRESP BODY: %(body)s\n", {
                'code': resp.status_code,
                'headers': resp.headers,
                'body': resp.text
            })

    def collect_metrics(self):
        body = {"driverType": self.driver_type}
        self.request('metrics', "POST", body=body)
